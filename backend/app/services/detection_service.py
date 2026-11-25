import logging
import os
import time
from typing import Any, Dict, List, Optional, Tuple
import uuid
from PIL import Image, ImageDraw, ImageFont
from sqlalchemy.orm import Session
from app.api.deps import verify_site_access
from app.config.settings import get_settings
from app.core.exceptions import InternalServerError, NotFoundError
from app.models.computer_vision import Detection, ZoneConfig
from app.models.inspections_media import Inspection, Media
from app.models.knowledge_compliance import Finding, Rule
from app.models.users_sites import User
from app.schemas.inspections import DetectionItem, FindingItem

logger = logging.getLogger(__name__)
settings = get_settings()

# Model class map for best_3.pt (YOLO11s)
MODEL_CLASSES = {
    0: 'person',
    1: 'safety_helmet',
    2: 'safety_vest',
    3: 'fire_extinguisher',
    4: 'fire_hose',
    5: 'pallet',
    6: 'fire',
    7: 'spill',
    8: 'safety_signage',
    9: 'exit_sign',
    10: 'empty_shelf',
    11: 'forklift',
    12: 'vehicle',
    13: 'obstacle',
    14: 'machinery',
    15: 'safety_cone',
}

CLASS_COLORS = {
    'person': (59, 130, 246),         # Blue
    'safety_helmet': (16, 185, 129),   # Emerald green
    'safety_vest': (245, 158, 11),     # Amber
    'fire_extinguisher': (239, 68, 68),# Red
    'fire_hose': (220, 38, 38),        # Dark red
    'pallet': (168, 85, 247),          # Purple
    'fire': (239, 68, 68),             # Red / Hazard
    'spill': (249, 115, 22),           # Orange / Hazard
    'safety_signage': (6, 182, 212),   # Cyan
    'exit_sign': (34, 197, 94),        # Green
    'empty_shelf': (100, 116, 139),    # Slate
    'forklift': (234, 88, 12),         # Deep orange
    'vehicle': (14, 165, 233),         # Sky blue
    'obstacle': (225, 29, 72),         # Rose
    'machinery': (217, 119, 6),        # Amber dark
    'safety_cone': (251, 146, 60),     # Orange cone
}


def point_in_polygon(x: float, y: float, poly: List[List[float]]) -> bool:
    """Ray-casting algorithm to test if (x, y) is inside polygon vertices."""
    if not poly or len(poly) < 3:
        return False
    n = len(poly)
    inside = False
    p1x, p1y = poly[0]
    for i in range(n + 1):
        p2x, p2y = poly[i % n]
        if y > min(p1y, p2y):
            if y <= max(p1y, p2y):
                if x <= max(p1x, p2x):
                    xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x if p1y != p2y else p1x
                    if p1x == p2x or x <= xinters:
                        inside = not inside
        p1x, p1y = p2x, p2y
    return inside


class DetectionService:
    """Detection Service powering AI inference with YOLO11s (best_3.pt)."""

    _model = None
    _weights_path = None

    @classmethod
    def get_weights_path(cls) -> str:
        """Resolve absolute path to best_3.pt weights."""
        if cls._weights_path and os.path.exists(cls._weights_path):
            return cls._weights_path

        candidates = [
            os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "weights", "best_3.pt")),
            os.path.abspath(os.path.join(os.getcwd(), "backend", "app", "weights", "best_3.pt")),
            os.path.abspath(os.path.join(os.getcwd(), "app", "weights", "best_3.pt")),
            os.path.abspath(settings.YOLO_MODEL_PATH),
        ]
        for p in candidates:
            if os.path.exists(p):
                cls._weights_path = p
                return p
        # Fall back to first candidate
        return candidates[0]

    @classmethod
    def load_model(cls):
        """Lazy load YOLO model singleton."""
        if cls._model is not None:
            return cls._model

        weights = cls.get_weights_path()
        if not os.path.exists(weights):
            logger.warning(f"Weights file not found at {weights}. Inference will run in fallback simulation mode.")
            return None

        try:
            from ultralytics import YOLO
            cls._model = YOLO(weights)
            logger.info(f"Loaded YOLO detection model successfully from {weights}")
            return cls._model
        except Exception as e:
            logger.error(f"Failed to load YOLO model: {e}")
            return None

    @classmethod
    def run_inference_on_file(
        cls,
        file_path: str,
        conf_threshold: float = 0.15,
        iou_threshold: float = 0.45,
    ) -> Tuple[List[Dict[str, Any]], float]:
        """Runs best_3.pt inference on an image file, returning raw detections and latency."""
        start_time = time.time()
        model = cls.load_model()

        if model is None or not os.path.exists(file_path):
            latency = (time.time() - start_time) * 1000
            return [], latency

        try:
            results = model(file_path, conf=conf_threshold, iou=iou_threshold, verbose=False)
            latency = (time.time() - start_time) * 1000

            parsed: List[Dict[str, Any]] = []
            if results and len(results) > 0:
                boxes = results[0].boxes
                for box in boxes:
                    xyxy = box.xyxy[0].tolist()  # [x1, y1, x2, y2]
                    conf = float(box.conf[0].item())
                    cls_id = int(box.cls[0].item())
                    class_name = MODEL_CLASSES.get(cls_id, model.names.get(cls_id, f"class_{cls_id}"))

                    parsed.append({
                        "bbox": [round(coord, 1) for coord in xyxy],
                        "confidence": round(conf, 4),
                        "class_id": cls_id,
                        "class_name": class_name,
                    })

            return parsed, latency
        except Exception as e:
            logger.error(f"Inference error on {file_path}: {e}")
            latency = (time.time() - start_time) * 1000
            return [], latency

    @classmethod
    def detect_direct_file(
        cls,
        file_bytes: bytes,
        filename: str,
        conf_threshold: float = 0.15,
        iou_threshold: float = 0.45,
    ) -> Dict[str, Any]:
        """Runs best_3.pt directly on uploaded file bytes and returns detections, class counts, dimensions, and base64 annotated image."""
        start_time = time.time()
        model = cls.load_model()
        if model is None:
            return {
                "image_width": 1200,
                "image_height": 800,
                "total_detections": 0,
                "class_counts": {},
                "detections": [],
                "annotated_image_url": "",
                "inference_time_ms": 0.0,
            }

        import tempfile
        ext = os.path.splitext(filename)[1] or ".jpg"
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name

        try:
            results = model.predict(source=tmp_path, conf=conf_threshold, imgsz=640, device="cpu", verbose=False)
            latency = (time.time() - start_time) * 1000
            r = results[0]
            orig_h, orig_w = int(r.orig_shape[0]), int(r.orig_shape[1])

            parsed = []
            class_counts = {}
            for i, box in enumerate(r.boxes, 1):
                cls_id = int(box.cls[0].item())
                cls_name = MODEL_CLASSES.get(cls_id, model.names.get(cls_id, f"class_{cls_id}"))
                conf = float(box.conf[0].item())
                xyxy = [round(x, 1) for x in box.xyxy[0].tolist()]
                class_counts[cls_name] = class_counts.get(cls_name, 0) + 1

                parsed.append({
                    "id": f"det-{i}",
                    "className": cls_name,
                    "bbox": xyxy,
                    "confidence": round(conf, 4),
                    "zone": "Active Work Zone",
                })

            import cv2, base64
            annotated_img = r.plot(line_width=2, font_size=20)
            success, buf = cv2.imencode(".jpg", annotated_img)
            b64_str = base64.b64encode(buf).decode("utf-8") if success else ""
            annotated_data_url = f"data:image/jpeg;base64,{b64_str}" if b64_str else ""

            return {
                "image_width": orig_w,
                "image_height": orig_h,
                "total_detections": len(parsed),
                "class_counts": class_counts,
                "detections": parsed,
                "annotated_image_url": annotated_data_url,
                "inference_time_ms": round(latency, 2),
            }
        except Exception as e:
            logger.error(f"Direct detection failed: {e}")
            return {
                "image_width": 1200,
                "image_height": 800,
                "total_detections": 0,
                "class_counts": {},
                "detections": [],
                "annotated_image_url": "",
                "inference_time_ms": 0.0,
            }
        finally:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass

    @classmethod
    def annotate_and_save_image(
        cls,
        original_abs_path: str,
        output_abs_path: str,
        detections: List[Dict[str, Any]],
    ) -> bool:
        """Renders bounding boxes and class badges onto original image and saves it."""
        if not os.path.exists(original_abs_path):
            return False

        try:
            with Image.open(original_abs_path) as img:
                img = img.convert("RGB")
                draw = ImageDraw.Draw(img)

                for det in detections:
                    bbox = det["bbox"]
                    x1, y1, x2, y2 = bbox
                    class_name = det["class_name"]
                    conf = det["confidence"]
                    color = CLASS_COLORS.get(class_name, (16, 185, 129))

                    # Draw rectangle outline
                    draw.rectangle([x1, y1, x2, y2], outline=color, width=3)

                    # Draw label background badge
                    label_text = f"{class_name} {int(conf * 100)}%"
                    label_h = 18
                    label_w = len(label_text) * 8 + 8
                    draw.rectangle([x1, max(0, y1 - label_h), x1 + label_w, y1], fill=color)
                    draw.text((x1 + 4, max(0, y1 - label_h) + 2), label_text, fill=(255, 255, 255))

                os.makedirs(os.path.dirname(output_abs_path), exist_ok=True)
                img.save(output_abs_path, format="JPEG", quality=90)
                return True
        except Exception as e:
            logger.error(f"Failed to annotate image: {e}")
            return False

    @classmethod
    def evaluate_spatial_zones(
        cls,
        detections: List[Dict[str, Any]],
        zones: List[ZoneConfig],
    ) -> List[Dict[str, Any]]:
        """Assigns zone names to detections based on polygon inclusion."""
        for det in detections:
            x1, y1, x2, y2 = det["bbox"]
            cx, cy = (x1 + x2) / 2.0, (y1 + y2) / 2.0
            det["zone"] = None

            for z in zones:
                # Expecting [[x, y], ...]
                points = z.coordinates
                if points and isinstance(points, list):
                    # In case format is [{"x": 100, "y": 200}] or [[100, 200]]
                    clean_poly = []
                    for pt in points:
                        if isinstance(pt, dict) and "x" in pt and "y" in pt:
                            clean_poly.append([float(pt["x"]), float(pt["y"])])
                        elif isinstance(pt, (list, tuple)) and len(pt) >= 2:
                            clean_poly.append([float(pt[0]), float(pt[1])])

                    if point_in_polygon(cx, cy, clean_poly):
                        det["zone"] = z.name
                        break

            if not det["zone"]:
                det["zone"] = "General Site Area"

        return detections

    @classmethod
    def _get_or_create_rule(
        cls,
        db: Session,
        name: str,
        rule_type: str = "required_object",
        policy_ref: str = "OSHA Standard 1926",
        severity: str = "high",
        parameters: Optional[Dict[str, Any]] = None,
    ) -> Rule:
        """Finds or seeds a rule to ensure valid foreign keys on Findings."""
        rule = db.query(Rule).filter(Rule.name == name).first()
        if not rule:
            rule = Rule(
                name=name,
                description=f"Automated compliance rule for {name}",
                rule_type=rule_type,
                parameters=parameters or {},
                policy_ref=policy_ref,
                severity=severity,
                is_active=True,
            )
            db.add(rule)
            db.flush()
        return rule

    @classmethod
    def evaluate_ppe_and_safety_rules(
        cls,
        db: Session,
        inspection: Inspection,
        detections: List[Dict[str, Any]],
    ) -> List[Finding]:
        """Evaluates compliance rules based on detected objects (PPE, Machinery, Fire, Spill)."""
        findings: List[Finding] = []
        rules = db.query(Rule).filter(Rule.is_active == True).all()
        rule_map = {r.name: r for r in rules}

        persons = [d for d in detections if d["class_name"] == "person"]
        helmets = [d for d in detections if d["class_name"] == "safety_helmet"]
        vests = [d for d in detections if d["class_name"] == "safety_vest"]
        forklifts = [d for d in detections if d["class_name"] in ("forklift", "machinery", "vehicle")]
        fires = [d for d in detections if d["class_name"] == "fire"]
        spills = [d for d in detections if d["class_name"] == "spill"]

        # 1. Hardhat rule check
        rule_ppe1 = rule_map.get("Hardhat Mandate on Active Site") or cls._get_or_create_rule(
            db, "Hardhat Mandate on Active Site", "required_object", "OSHA 1926.100(a)", "critical"
        )

        if persons:
            unhelmeted_persons = 0
            for p in persons:
                px1, py1, px2, py2 = p["bbox"]
                head_top = py1
                head_bottom = py1 + (py2 - py1) * 0.35
                has_helmet = any(
                    (hx1 < px2 and hx2 > px1 and hy2 >= head_top and hy1 <= head_bottom)
                    for h in helmets
                    for hx1, hy1, hx2, hy2 in [h["bbox"]]
                )
                if not has_helmet:
                    unhelmeted_persons += 1

            if unhelmeted_persons > 0:
                f = Finding(
                    inspection_id=inspection.id,
                    rule_id=rule_ppe1.id,
                    status="fail",
                    severity="critical",
                    reasoning=f"{unhelmeted_persons} of {len(persons)} detected worker(s) observed without mandatory safety helmet.",
                    evidence_ids=[str(p.get("id", "")) for p in persons],
                )
                findings.append(f)
            else:
                f = Finding(
                    inspection_id=inspection.id,
                    rule_id=rule_ppe1.id,
                    status="pass",
                    severity="critical",
                    reasoning=f"All {len(persons)} detected worker(s) are compliant with safety helmets.",
                )
                findings.append(f)

        # 2. Fire and Spill hazard detection
        rule_hazard = rule_map.get("Hazard Elimination & Fire Safety") or cls._get_or_create_rule(
            db, "Hazard Elimination & Fire Safety", "forbidden_object", "OSHA 1926.24", "critical"
        )

        if fires:
            findings.append(Finding(
                inspection_id=inspection.id,
                rule_id=rule_hazard.id,
                status="fail",
                severity="critical",
                reasoning="CRITICAL SAFETY HAZARD: Active fire detected in camera field of view.",
            ))

        if spills:
            findings.append(Finding(
                inspection_id=inspection.id,
                rule_id=rule_hazard.id,
                status="fail",
                severity="high",
                reasoning="Slip and fall hazard: Industrial liquid spill detected on surface.",
            ))

        # 3. Machinery in pedestrian clear corridors
        rule_clear_zone = rule_map.get("Vehicle & Pedestrian Spatial Separation") or cls._get_or_create_rule(
            db, "Vehicle & Pedestrian Spatial Separation", "clear_zone", "Site Safety Manual Sec 5.3", "high"
        )

        for fl in forklifts:
            z_name = (fl.get("zone") or "").lower()
            if "pedestrian" in z_name or "walkway" in z_name:
                findings.append(Finding(
                    inspection_id=inspection.id,
                    rule_id=rule_clear_zone.id,
                    status="fail",
                    severity="high",
                    reasoning=f"Spatial clear zone violation: {fl['class_name']} detected operating inside {fl['zone']}.",
                ))

        return findings

    @classmethod
    def detect_media(
        cls,
        db: Session,
        media_id: uuid.UUID,
        current_user: User,
        conf_threshold: float = 0.25,
        iou_threshold: float = 0.45,
        save_annotated: bool = True,
    ) -> Dict[str, Any]:
        """Executes full detection workflow on a single media file."""
        media = db.query(Media).filter(Media.id == media_id).first()
        if not media:
            raise NotFoundError(message=f"Media {media_id} not found.")

        inspection = db.query(Inspection).filter(Inspection.id == media.inspection_id).first()
        if not inspection:
            raise NotFoundError(message=f"Inspection {media.inspection_id} not found.")

        verify_site_access(inspection.site_id, current_user, db)

        # Resolve storage path
        storage_root = os.path.abspath(settings.MEDIA_STORAGE_PATH)
        abs_media_path = os.path.abspath(os.path.join(storage_root, media.path))

        # 1. Run YOLO inference
        raw_detections, latency_ms = cls.run_inference_on_file(
            abs_media_path,
            conf_threshold=conf_threshold,
            iou_threshold=iou_threshold,
        )

        # 2. Fetch site spatial zones & evaluate
        zones = db.query(ZoneConfig).filter(ZoneConfig.site_id == inspection.site_id).all()
        evaluated_dets = cls.evaluate_spatial_zones(raw_detections, zones)

        # 3. Clean up existing detections for this media
        db.query(Detection).filter(Detection.media_id == media_id).delete()

        # 4. Save new detections to DB
        created_items: List[DetectionItem] = []
        class_counts: Dict[str, int] = {}

        for det in evaluated_dets:
            cname = det["class_name"]
            class_counts[cname] = class_counts.get(cname, 0) + 1

            record = Detection(
                media_id=media.id,
                class_name=cname,
                bbox=det["bbox"],
                confidence=det["confidence"],
                zone=det["zone"],
                model_version="yolo11s_sitesense_best3",
            )
            db.add(record)
            db.flush()

            created_items.append(DetectionItem(
                id=record.id,
                media_id=record.media_id,
                class_name=record.class_name,
                bbox=record.bbox,
                confidence=record.confidence,
                zone=record.zone,
                frame_no=record.frame_no,
            ))

        # 5. Visual annotation
        annotated_url = None
        if save_annotated and evaluated_dets and os.path.exists(abs_media_path):
            dir_name = os.path.dirname(abs_media_path)
            annotated_abs_path = os.path.join(dir_name, f"annotated_{media.id}.jpg")
            if cls.annotate_and_save_image(abs_media_path, annotated_abs_path, evaluated_dets):
                media.annotated_path = os.path.relpath(annotated_abs_path, storage_root).replace("\\", "/")
                media.is_annotated = True
                annotated_url = f"{settings.API_V1_PREFIX}/media/{media.id}/annotated"

        # 6. Evaluate findings & update pass rate
        findings = cls.evaluate_ppe_and_safety_rules(db, inspection, evaluated_dets)
        for f in findings:
            db.add(f)

        violations_count = sum(1 for f in findings if f.status == "fail")
        total_evals = len(findings)
        if total_evals > 0:
            pass_rate = round(((total_evals - violations_count) / total_evals) * 100.0, 1)
            inspection.pass_rate = pass_rate
        inspection.status = "completed"

        db.commit()

        return {
            "media_id": media.id,
            "inspection_id": inspection.id,
            "model_version": "yolo11s_sitesense_best3",
            "total_detections": len(created_items),
            "detections": created_items,
            "class_counts": class_counts,
            "violations_detected": violations_count,
            "annotated_media_url": annotated_url,
            "inference_time_ms": round(latency_ms, 2),
        }

    @classmethod
    def detect_inspection(
        cls,
        db: Session,
        inspection_id: uuid.UUID,
        current_user: User,
        conf_threshold: float = 0.25,
        iou_threshold: float = 0.45,
    ) -> Dict[str, Any]:
        """Runs best_3.pt detection across all images and videos belonging to an inspection."""
        inspection = db.query(Inspection).filter(Inspection.id == inspection_id).first()
        if not inspection:
            raise NotFoundError(message=f"Inspection {inspection_id} not found.")

        verify_site_access(inspection.site_id, current_user, db)

        media_records = db.query(Media).filter(Media.inspection_id == inspection_id).all()
        total_latency = 0.0
        all_detections: List[DetectionItem] = []
        aggregated_classes: Dict[str, int] = {}

        processed = 0
        for m in media_records:
            if m.type in ("image", "video"):
                res = cls.detect_media(
                    db,
                    m.id,
                    current_user,
                    conf_threshold=conf_threshold,
                    iou_threshold=iou_threshold,
                )
                processed += 1
                total_latency += res.get("inference_time_ms", 0.0)
                all_detections.extend(res.get("detections", []))
                for c, count in res.get("class_counts", {}).items():
                    aggregated_classes[c] = aggregated_classes.get(c, 0) + count

        db.refresh(inspection)
        findings = db.query(Finding).filter(Finding.inspection_id == inspection_id).all()
        finding_items = [
            FindingItem(
                id=f.id,
                inspection_id=f.inspection_id,
                rule_id=f.rule_id,
                status=f.status,
                evidence_ids=f.evidence_ids or [],
                reasoning=f.reasoning,
                severity=f.severity,
            )
            for f in findings
        ]

        total_violations = sum(1 for f in findings if f.status == "fail")

        return {
            "inspection_id": inspection.id,
            "media_processed": processed,
            "total_detections": len(all_detections),
            "total_violations": total_violations,
            "new_findings_count": len(findings),
            "pass_rate": inspection.pass_rate,
            "status": inspection.status,
            "detections": all_detections,
            "findings": finding_items,
            "class_counts": aggregated_classes,
            "total_latency_ms": round(total_latency, 2),
        }
