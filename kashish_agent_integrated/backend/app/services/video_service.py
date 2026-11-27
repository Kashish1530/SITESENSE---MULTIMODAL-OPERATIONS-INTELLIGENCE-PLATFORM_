import logging
import os
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np
from sqlalchemy.orm import Session

from app.config.settings import get_settings
from app.core.exceptions import NotFoundError
from app.models.computer_vision import Detection, TrackingResult, ZoneConfig
from app.models.inspections_media import Inspection, Media
from app.models.knowledge_compliance import Finding
from app.models.users_sites import User
from app.services.detection_service import DetectionService
from app.services.ocr_service import OCRService
from app.services.storage_service import storage_service

logger = logging.getLogger("app.video")
settings = get_settings()

# Ensure <repo_root>/src is importable for ZoneEngine & VisualAnnotator
_SERVICE_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SERVICE_DIR.parent.parent.parent.parent
_SRC_DIR = str(_REPO_ROOT / "src")
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)


class _SimpleIoUTracker:
    """Lightweight persistent IoU tracker for merged best_3.pt + best_2.pt detections."""

    def __init__(self, iou_threshold: float = 0.30, max_missed: int = 15):
        self.iou_threshold = iou_threshold
        self.max_missed = max_missed
        self.next_id = 1
        self.tracks: Dict[int, Dict[str, Any]] = {}

    def update(self, detections: List[Dict[str, Any]], frame_idx: int) -> List[Dict[str, Any]]:
        matched_track_ids = set()
        results: List[Dict[str, Any]] = []

        for det in detections:
            bbox = det["bbox"]
            cls_name = det["class_name"]
            best_tid = None
            best_iou = self.iou_threshold

            for tid, trk in self.tracks.items():
                if tid in matched_track_ids or trk["class_name"] != cls_name:
                    continue
                iou = DetectionService._calculate_iou(bbox, trk["bbox"])
                if iou >= best_iou:
                    best_iou = iou
                    best_tid = tid

            if best_tid is None:
                best_tid = self.next_id
                self.next_id += 1
                self.tracks[best_tid] = {
                    "track_id": best_tid,
                    "class_id": det["class_id"],
                    "class_name": cls_name,
                    "bbox": bbox,
                    "start_frame": frame_idx,
                    "end_frame": frame_idx,
                    "missed": 0,
                    "trajectory": [],
                }

            trk = self.tracks[best_tid]
            trk["bbox"] = bbox
            trk["end_frame"] = frame_idx
            trk["missed"] = 0
            cx = round((bbox[0] + bbox[2]) / 2.0, 1)
            cy = round((bbox[1] + bbox[3]) / 2.0, 1)
            trk["trajectory"].append([cx, cy, frame_idx])
            if len(trk["trajectory"]) > 120:
                trk["trajectory"] = trk["trajectory"][-120:]

            matched_track_ids.add(best_tid)
            results.append({
                "track_id": best_tid,
                "class_id": det["class_id"],
                "class_name": cls_name,
                "confidence": det["confidence"],
                "bbox": [int(round(v)) for v in bbox],
            })

        stale = []
        for tid, trk in self.tracks.items():
            if tid not in matched_track_ids:
                trk["missed"] += 1
                if trk["missed"] > self.max_missed:
                    stale.append(tid)
        for tid in stale:
            del self.tracks[tid]

        return results


class VideoService:
    """
    Processes uploaded videos end-to-end:
    1. Detection (ONLY best_3.pt + best_2.pt with NMS) + persistent tracking + ZoneEngine analysis
    2. Saves annotated video to local storage + MinIO + Neon (media.annotated_path)
    3. Captures violation/alert evidence snapshots -> uploads to MinIO
    4. Runs OCR extraction + English translation on all evidence snapshots -> Neon 5 OCR tables
    """

    @staticmethod
    def _build_zone_config_dict(zones: List[ZoneConfig]) -> Dict[str, Any]:
        """Convert Neon ZoneConfig rows into the dictionary format expected by ZoneEngine."""
        zones_dict: Dict[str, Any] = {}
        lines_dict: Dict[str, Any] = {}

        for z in zones:
            coords = z.coordinates or []
            clean_coords: List[List[int]] = []
            for pt in coords:
                if isinstance(pt, dict) and "x" in pt and "y" in pt:
                    clean_coords.append([int(round(float(pt["x"]))), int(round(float(pt["y"])))])
                elif isinstance(pt, (list, tuple)) and len(pt) >= 2:
                    clean_coords.append([int(round(float(pt[0]))), int(round(float(pt[1])))])

            if z.zone_type == "counting_line" and len(clean_coords) >= 2:
                lines_dict[str(z.id)] = {
                    "line_id": str(z.id),
                    "name": z.name,
                    "coordinates": clean_coords[:2],
                    "count_classes": [0, 11, 12],
                }
            elif len(clean_coords) >= 3:
                rules_cfg = z.rules_config if isinstance(z.rules_config, dict) else {}
                zones_dict[str(z.id)] = {
                    "zone_id": str(z.id),
                    "zone_name": z.name,
                    "zone_type": rules_cfg.get("zone_type", "exclusion"),
                    "alert_severity": rules_cfg.get("alert_severity", "HIGH"),
                    "coordinates": clean_coords,
                    "prohibited_classes": rules_cfg.get("prohibited_classes", [0, 11, 12, 14]),
                    "blockage_threshold_seconds": float(rules_cfg.get("blockage_threshold_seconds", 2.0)),
                    "description": f"Site zone: {z.name}",
                }

        return {
            "camera_id": "CAM-UPLOAD",
            "zones": zones_dict,
            "counting_lines": lines_dict,
            "dynamic_danger_zones": {
                "enabled": True,
                "machinery_classes": [11, 12, 14],
                "target_classes": [0],
                "danger_radius_px": 180.0,
                "warning_radius_px": 260.0,
                "alert_severity": "CRITICAL",
            },
        }

    @classmethod
    def process_video(
        cls,
        db: Session,
        media_id: uuid.UUID,
        current_user: User,
        conf_threshold: float = 0.25,
        iou_threshold: float = 0.45,
        sample_stride: Optional[int] = None,
        max_ocr_snapshots: int = 5,
        progress_callback=None,
    ) -> Dict[str, Any]:
        """Run full video detection, tracking, zone analysis, evidence snapshots, and OCR."""
        import torch
        from annotator import VisualAnnotator
        from zone_engine import ZoneEngine

        t0 = time.time()
        media = db.query(Media).filter(Media.id == media_id).first()
        if not media:
            raise NotFoundError(message=f"Media {media_id} not found.")

        inspection = db.query(Inspection).filter(Inspection.id == media.inspection_id).first()
        if not inspection:
            raise NotFoundError(message=f"Inspection {media.inspection_id} not found.")

        abs_video_path = str(storage_service.get_absolute_path(media.path))
        storage_root = str(storage_service.base_dir)
        models = DetectionService.load_models()

        cap = cv2.VideoCapture(abs_video_path)
        if not cap.isOpened():
            raise RuntimeError(f"Cannot open video file: {abs_video_path}")

        fps = float(cap.get(cv2.CAP_PROP_FPS) or 25.0)
        if fps <= 0 or fps > 120:
            fps = 25.0
        total_frames_est = max(1, int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 1))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 640)
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 480)

        # Adaptive stride (~5 detections/sec) & smaller imgsz on CPU for 3x faster inference
        use_cuda = torch.cuda.is_available()
        infer_imgsz = 640 if use_cuda else 480
        if sample_stride is None:
            sample_stride = 2 if use_cuda else max(4, int(round(fps / 5.0)))

        video_dir = os.path.dirname(abs_video_path)
        annotated_video_name = f"annotated_{media.id}.mp4"
        annotated_video_abs = os.path.join(video_dir, annotated_video_name)
        evidence_dir = os.path.join(video_dir, f"evidence_{media.id}")
        os.makedirs(evidence_dir, exist_ok=True)

        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(annotated_video_abs, fourcc, fps, (width, height))

        site_zones = db.query(ZoneConfig).filter(ZoneConfig.site_id == inspection.site_id).all()
        zone_engine = ZoneEngine(config_source=cls._build_zone_config_dict(site_zones))
        tracker = _SimpleIoUTracker(iou_threshold=0.30, max_missed=15)

        # Clear any prior detections / tracking for idempotency
        db.query(Detection).filter(Detection.media_id == media.id).delete()
        db.query(TrackingResult).filter(TrackingResult.media_id == media.id).delete()

        all_tracks_history: Dict[int, Dict[str, Any]] = {}
        class_counts: Dict[str, int] = {}
        evidence_snapshots: List[Dict[str, Any]] = []
        captured_alert_sigs = set()
        captured_snapshot_frames = set()
        violations_list: List[Dict[str, Any]] = []
        line_crossings_count = 0
        total_detections_count = 0

        last_tracked: List[Dict[str, Any]] = []
        last_violations: List[Dict[str, Any]] = []
        fallback_frame_path: Optional[str] = None
        frame_idx = 0

        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                timestamp = frame_idx / fps

                if frame_idx % max(1, sample_stride) == 0 and models:
                    raw_all: List[Dict[str, Any]] = []
                    active_name, active_model = next(iter(models.items()))
                    try:
                        with torch.inference_mode():
                            results = active_model(
                                frame,
                                conf=conf_threshold,
                                iou=iou_threshold,
                                imgsz=infer_imgsz,
                                verbose=False,
                            )
                    except Exception as primary_exc:
                        logger.warning(f"Primary model '{active_name}' failed on frame {frame_idx} ({primary_exc}); switching to best_2.pt fallback.")
                        fb_models = DetectionService.get_fallback_models()
                        if fb_models:
                            models = fb_models
                            active_name, active_model = next(iter(models.items()))
                            with torch.inference_mode():
                                results = active_model(
                                    frame,
                                    conf=conf_threshold,
                                    iou=iou_threshold,
                                    imgsz=infer_imgsz,
                                    verbose=False,
                                )
                        else:
                            results = []

                    if results and len(results) > 0:
                        for box in results[0].boxes:
                            xyxy = box.xyxy[0].tolist()
                            conf = float(box.conf[0].item())
                            cls_id = int(box.cls[0].item())
                            cname = active_model.names.get(cls_id, f"class_{cls_id}")
                            raw_all.append({
                                "bbox": [round(c, 1) for c in xyxy],
                                "confidence": round(conf, 4),
                                "class_id": cls_id,
                                "class_name": cname,
                                "source_model": active_name,
                            })

                    tracked = tracker.update(raw_all, frame_idx)
                    last_tracked = tracked

                    for trk_obj in tracked:
                        tid = trk_obj["track_id"]
                        cname = trk_obj["class_name"]
                        class_counts[cname] = class_counts.get(cname, 0) + 1
                        total_detections_count += 1

                        if tid in tracker.tracks:
                            all_tracks_history[tid] = dict(tracker.tracks[tid])

                        # Persist sampled detection row
                        if frame_idx % (max(1, sample_stride) * 5) == 0:
                            db.add(
                                Detection(
                                    media_id=media.id,
                                    class_name=cname,
                                    bbox=[float(v) for v in trk_obj["bbox"]],
                                    confidence=trk_obj["confidence"],
                                    zone="Video Tracked Zone",
                                    frame_no=frame_idx,
                                    track_id=tid,
                                    model_version="yolo_best3_best2_ensemble",
                                )
                            )

                    violations, crossings = zone_engine.evaluate_tracks(tracked, timestamp)
                    prox_alerts, _ = zone_engine.evaluate_dynamic_machinery_danger_zones(tracked, timestamp)
                    combined_alerts = list(violations) + [
                        {
                            "zone_id": "dynamic_machinery",
                            "zone_name": "Machinery Proximity Zone",
                            "track_id": a.get("person_id", 0),
                            "class_id": 0,
                            "class_name": "person",
                            "severity": a.get("severity", "CRITICAL"),
                            "dwell_time_seconds": 0.0,
                            "alert_type": "machinery_proximity",
                        }
                        for a in prox_alerts
                    ]
                    # Also flag fire / spill hazards in frame
                    for trk_obj in tracked:
                        if trk_obj["class_name"] in ("fire", "spill"):
                            combined_alerts.append({
                                "zone_id": f"hazard_{trk_obj['class_name']}",
                                "zone_name": "Active Hazard",
                                "track_id": trk_obj["track_id"],
                                "class_id": trk_obj["class_id"],
                                "class_name": trk_obj["class_name"],
                                "severity": "CRITICAL",
                                "dwell_time_seconds": 0.0,
                                "alert_type": f"{trk_obj['class_name']}_detected",
                            })

                    last_violations = combined_alerts
                    line_crossings_count += len(crossings)

                active_viol_zones = {v["zone_id"] for v in last_violations if v.get("zone_id")}
                annotated_frame = frame.copy()
                annotated_frame = VisualAnnotator.draw_zones(annotated_frame, zone_engine.zones, active_viol_zones)
                annotated_frame = VisualAnnotator.draw_counting_lines(annotated_frame, zone_engine.counting_lines)
                annotated_frame = VisualAnnotator.draw_tracked_objects(annotated_frame, last_tracked, last_violations)
                annotated_frame = VisualAnnotator.draw_hud(
                    annotated_frame, frame_idx, timestamp, last_violations, len(last_tracked), zone_engine.counting_lines
                )

                # Save a fallback keyframe snapshot (first frame with detections or frame 0)
                if fallback_frame_path is None and (last_tracked or frame_idx == 0):
                    fb_path = os.path.join(evidence_dir, f"snapshot_{media.id}_f{frame_idx}.jpg")
                    cv2.imwrite(fb_path, annotated_frame)
                    fallback_frame_path = fb_path

                # Capture at most ONE evidence snapshot per unique frame with new alerts
                for viol in last_violations:
                    sig = f"{viol.get('zone_id')}_{viol.get('track_id')}_{viol.get('alert_type', 'zone')}"
                    if sig not in captured_alert_sigs:
                        captured_alert_sigs.add(sig)
                        violations_list.append(viol)
                        if frame_idx not in captured_snapshot_frames:
                            captured_snapshot_frames.add(frame_idx)
                            snap_name = f"evidence_{media.id}_f{frame_idx}_{len(evidence_snapshots) + 1}.jpg"
                            snap_abs = os.path.join(evidence_dir, snap_name)
                            cv2.imwrite(snap_abs, annotated_frame)
                            rel_snap = os.path.relpath(snap_abs, storage_root).replace("\\", "/")
                            storage_service.upload_local_file(snap_abs, rel_snap, content_type="image/jpeg")
                            evidence_snapshots.append({
                                "path": snap_abs,
                                "relative_path": rel_snap,
                                "frame_no": frame_idx,
                                "alert": viol,
                            })

                writer.write(annotated_frame)
                frame_idx += 1
                if progress_callback and frame_idx % 25 == 0:
                    pct = min(75, 10 + int((frame_idx / total_frames_est) * 65))
                    progress_callback(pct, f"video_tracking_frame_{frame_idx}_of_{total_frames_est}")
        finally:
            cap.release()
            writer.release()

        # If no violation snapshots were triggered, use fallback annotated frame so OCR still inspects keyframe
        if not evidence_snapshots and fallback_frame_path and os.path.exists(fallback_frame_path):
            rel_fb = os.path.relpath(fallback_frame_path, storage_root).replace("\\", "/")
            storage_service.upload_local_file(fallback_frame_path, rel_fb, content_type="image/jpeg")
            evidence_snapshots.append({
                "path": fallback_frame_path,
                "relative_path": rel_fb,
                "frame_no": 0,
                "alert": {"zone_name": "Keyframe Evidence", "severity": "INFO"},
            })

        # Upload annotated video to MinIO & update Media in Neon
        rel_annotated_video = os.path.relpath(annotated_video_abs, storage_root).replace("\\", "/")
        media.annotated_path = rel_annotated_video
        media.is_annotated = True
        storage_service.upload_local_file(annotated_video_abs, rel_annotated_video, content_type="video/mp4")

        # Persist TrackingResult rows in Neon
        for tid, trk in all_tracks_history.items():
            dwell_s = round((trk["end_frame"] - trk["start_frame"]) / fps, 2)
            db.add(
                TrackingResult(
                    media_id=media.id,
                    track_id=tid,
                    class_name=trk["class_name"],
                    start_frame=trk["start_frame"],
                    end_frame=trk["end_frame"],
                    dwell_time_seconds=dwell_s,
                    trajectory=trk["trajectory"],
                    counting_line_crossed=line_crossings_count > 0,
                )
            )

        # Persist Finding rows for video violations/alerts
        if violations_list:
            rule_video = DetectionService._get_or_create_rule(
                db, "Video Zone & Proximity Safety", "clear_zone", "Site Safety Manual Sec 5.3", "high"
            )
            for v in violations_list[:10]:
                db.add(
                    Finding(
                        inspection_id=inspection.id,
                        rule_id=rule_video.id,
                        status="fail",
                        severity=str(v.get("severity", "high")).lower(),
                        reasoning=f"Video alert in {v.get('zone_name', 'Site Zone')} (Track {v.get('track_id')}, class={v.get('class_name')}).",
                        evidence_ids=[s["relative_path"] for s in evidence_snapshots],
                    )
                )

        # Run OCR + English translation on up to max_ocr_snapshots representative evidence snapshots -> JSON + 5 Neon OCR tables
        ocr_reports: List[Dict[str, Any]] = []
        ocr_targets = evidence_snapshots[:max_ocr_snapshots]
        for s_idx, snap in enumerate(ocr_targets, start=1):
            if progress_callback:
                pct = 75 + int((s_idx / max(1, len(ocr_targets))) * 22)
                progress_callback(min(97, pct), f"ocr_snapshot_{s_idx}_of_{len(ocr_targets)}")
            try:
                ocr_res = OCRService.process_annotated_image(
                    db=db,
                    media=media,
                    annotated_image_path=snap["path"],
                    site_id=str(inspection.site_id),
                )
                ocr_reports.append({
                    "report_id": ocr_res.get("report_id"),
                    "snapshot_path": snap["relative_path"],
                    "json_path": ocr_res.get("json_path"),
                    "full_text": ocr_res.get("full_text", ""),
                    "translated_text": ocr_res.get("translated_text"),
                    "is_translated": ocr_res.get("is_translated", False),
                    "entities_count": ocr_res.get("entities_count", 0),
                })
            except Exception as ocr_exc:
                logger.warning(f"OCR failed on video snapshot {snap['path']}: {ocr_exc}")

        meta = dict(media.metadata_json) if isinstance(media.metadata_json, dict) else {}
        meta["evidence_snapshots"] = [s["relative_path"] for s in evidence_snapshots]
        meta["ocr_report_ids"] = [r["report_id"] for r in ocr_reports if r.get("report_id")]
        media.metadata_json = meta

        inspection.status = "completed"
        db.commit()
        db.refresh(media)

        elapsed_ms = round((time.time() - t0) * 1000.0, 2)
        return {
            "media_id": str(media.id),
            "filename": media.filename,
            "media_type": "video",
            "annotated_path": media.annotated_path,
            "annotated_media_url": f"{settings.API_V1_PREFIX}/media/{media.id}/annotated",
            "frames_processed": frame_idx,
            "unique_tracks": len(all_tracks_history),
            "total_detections": total_detections_count,
            "class_counts": class_counts,
            "violations_detected": len(violations_list),
            "evidence_snapshots_count": len(evidence_snapshots),
            "evidence_snapshots": [s["relative_path"] for s in evidence_snapshots],
            "ocr_reports_count": len(ocr_reports),
            "ocr_reports": ocr_reports,
            "processing_time_ms": elapsed_ms,
        }
