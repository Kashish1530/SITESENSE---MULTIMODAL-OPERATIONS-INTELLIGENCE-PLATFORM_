import base64
import json
import logging
import os
import sys
import urllib.parse
import urllib.request
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.inspections_media import Inspection, Media
from app.models.site_text_intelligence import (
    SiteTextComplianceCheck,
    SiteTextEntity,
    SiteTextGenAIContext,
    SiteTextReport,
    SiteTextReviewQueue,
)
from app.services.storage_service import storage_service

logger = logging.getLogger("app.ocr")

# Ensure <repo_root>/src is importable so `ocr_module` can be loaded
_SERVICE_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SERVICE_DIR.parent.parent.parent.parent
_SRC_DIR = str(_REPO_ROOT / "src")
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)


class OCRService:
    """Runs PaddleOCR + SiteIntelligenceExtractor on annotated images and persists JSON to Neon OCR tables."""

    _engine = None
    _extractor = None

    @classmethod
    def _get_engine(cls):
        if cls._engine is None:
            from ocr_module.ocr_engine import OCREngine

            cls._engine = OCREngine(enable_preprocessing=True)
        return cls._engine

    @classmethod
    def _get_extractor(cls):
        if cls._extractor is None:
            from ocr_module.site_intelligence import SiteIntelligenceExtractor

            cls._extractor = SiteIntelligenceExtractor()
        return cls._extractor

    @staticmethod
    def _encode_image_base64(image_path: str) -> Optional[str]:
        try:
            with open(image_path, "rb") as f:
                return base64.b64encode(f.read()).decode("utf-8")
        except Exception as exc:
            logger.warning(f"Could not base64-encode annotated image '{image_path}': {exc}")
            return None

    @staticmethod
    def _translate_to_english(text: str) -> Dict[str, Any]:
        """Detect non-English OCR text and translate it to English."""
        if not text or not text.strip():
            return {"detected_lang": "en", "translated_text": None, "is_translated": False}

        clean_strip = text.strip()
        if clean_strip.replace("-", "").replace("_", "").replace(".", "").isalnum() and len(clean_strip) <= 6:
            return {"detected_lang": "en", "translated_text": None, "is_translated": False}

        url = (
            "https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl=en&dt=t&q="
            + urllib.parse.quote(text)
        )
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        try:
            with urllib.request.urlopen(req, timeout=6) as response:
                data = json.loads(response.read().decode("utf-8"))
                translated_pieces = [sentence[0] for sentence in data[0] if sentence[0]]
                translated = "".join(translated_pieces).strip()
                src_lang = str(data[2]).lower() if len(data) > 2 and data[2] else "auto"

                is_trans = bool(
                    translated
                    and src_lang not in ("en", "und")
                    and translated.lower() != clean_strip.lower()
                )
                return {
                    "detected_lang": src_lang,
                    "translated_text": translated if is_trans else None,
                    "is_translated": is_trans,
                }
        except Exception as exc:
            logger.warning(f"Google gtx translation failed ({exc}); trying deep_translator fallback.")
            try:
                from deep_translator import GoogleTranslator

                translated = (GoogleTranslator(source="auto", target="en").translate(text) or "").strip()
                is_trans = bool(translated and translated.lower() != clean_strip.lower())
                return {
                    "detected_lang": "auto",
                    "translated_text": translated if is_trans else None,
                    "is_translated": is_trans,
                }
            except Exception as exc2:
                logger.warning(f"deep_translator fallback also failed: {exc2}")
                return {"detected_lang": "auto", "translated_text": None, "is_translated": False}

    @classmethod
    def process_annotated_image(
        cls,
        db: Session,
        media: Media,
        annotated_image_path: str,
        site_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Run OCR extraction on an annotated image, save JSON output to storage/MinIO,
        and persist structured records into the 5 Neon OCR tables:
        ocr_reports, ocr_entities, ocr_review_queue, ocr_compliance_checks, ocr_genai_contexts.
        """
        if not annotated_image_path or not os.path.exists(annotated_image_path):
            raise FileNotFoundError(f"Annotated image not found at '{annotated_image_path}'")

        # Resolve site_id from inspection if not explicitly provided
        resolved_site_id = site_id
        if not resolved_site_id:
            inspection = db.query(Inspection).filter(Inspection.id == media.inspection_id).first()
            resolved_site_id = str(inspection.site_id) if inspection else "SITE-DEFAULT"

        engine = cls._get_engine()
        extractor = cls._get_extractor()

        # 1. Run OCR on the YOLO-annotated image
        ocr_response = engine.process_image(annotated_image_path, save_outputs=False)
        raw_full_text = ocr_response.full_text if ocr_response.success else ""

        # 1b. Translate non-English text to English
        translation = cls._translate_to_english(raw_full_text)
        translated_text = translation["translated_text"]
        is_translated = translation["is_translated"]
        detected_lang = translation["detected_lang"]

        # 2. Build Site Intelligence JSON report (include translated text if non-English)
        media_label = media.filename or os.path.basename(annotated_image_path)
        intel_report = extractor.analyze(
            media_name=media_label,
            ocr_results=ocr_response.extracted_text if ocr_response.success else [],
            full_text=translated_text if is_translated and translated_text else raw_full_text,
            processing_time_ms=ocr_response.processing_time_ms,
            site_id=resolved_site_id,
        )
        intel_report.inspection_id = str(media.inspection_id)

        report_json = intel_report.model_dump(mode="json")
        report_json["media_id"] = str(media.id)
        report_json["annotated_path"] = media.annotated_path
        report_json["full_text"] = raw_full_text
        report_json["translated_text"] = translated_text
        report_json["is_translated"] = is_translated
        report_json["detected_language"] = detected_lang

        # 3. Save JSON file locally and upload to MinIO if available
        json_filename = f"ocr_{media.id}.json"
        json_abs_path = os.path.join(os.path.dirname(annotated_image_path), json_filename)
        with open(json_abs_path, "w", encoding="utf-8") as jf:
            json.dump(report_json, jf, indent=2, ensure_ascii=False)

        rel_json_path = os.path.relpath(json_abs_path, str(storage_service.base_dir)).replace("\\", "/")
        storage_service.upload_local_file(json_abs_path, rel_json_path, content_type="application/json")

        # 4. Persist into the 5 Neon OCR tables
        annotated_b64 = cls._encode_image_base64(annotated_image_path)

        report_row = SiteTextReport(
            report_id=uuid.uuid4(),
            site_id=resolved_site_id,
            inspection_id=str(media.inspection_id),
            media_name=media_label,
            full_text=raw_full_text,
            translated_text=translated_text,
            is_translated=is_translated,
            processing_time_ms=float(intel_report.processing_time_ms or 0.0),
            annotated_image_base64=annotated_b64,
        )
        db.add(report_row)
        db.flush()

        for ent in intel_report.entities:
            bbox = [[float(pt[0]), float(pt[1])] for pt in (ent.bounding_box or [])]
            conf = max(0.0, min(1.0, float(ent.confidence)))
            db.add(
                SiteTextEntity(
                    entity_id=uuid.uuid4(),
                    report_id=report_row.report_id,
                    entity_type=ent.entity_type.value,
                    raw_text=ent.raw_text,
                    normalized_value=ent.normalized_value,
                    confidence=conf,
                    bounding_box=bbox,
                    verification_status=ent.verification_status.value,
                    review_reason=ent.review_reason,
                )
            )

        for rev in intel_report.review_queue_items:
            bbox = [[float(pt[0]), float(pt[1])] for pt in (rev.bounding_box or [])]
            conf = max(0.0, min(1.0, float(rev.confidence)))
            db.add(
                SiteTextReviewQueue(
                    entity_id=uuid.uuid4(),
                    report_id=report_row.report_id,
                    entity_type=rev.entity_type.value,
                    raw_text=rev.raw_text,
                    normalized_value=rev.normalized_value,
                    confidence=conf,
                    bounding_box=bbox,
                    verification_status=rev.verification_status.value,
                    review_reason=rev.review_reason,
                    review_status="pending",
                )
            )

        for chk in intel_report.compliance_checks:
            db.add(
                SiteTextComplianceCheck(
                    check_id=uuid.uuid4(),
                    report_id=report_row.report_id,
                    rule_id=chk.rule_id,
                    rule_name=chk.rule_name,
                    policy_reference=chk.policy_reference,
                    status=chk.status.value,
                    details=chk.details,
                    evidence_text=chk.evidence_text,
                )
            )

        genai_ctx = intel_report.genai_context or {}
        prompt_text = genai_ctx.get("prompt_ready_context") or f"OCR Report for {media_label}: {intel_report.full_text}"
        context_metadata = {
            "structured_evidence": genai_ctx.get("structured_evidence", {}),
            "suggested_llm_actions": genai_ctx.get("suggested_llm_actions", []),
            "ocr_json": report_json,
        }
        db.add(
            SiteTextGenAIContext(
                context_id=uuid.uuid4(),
                report_id=report_row.report_id,
                prompt=prompt_text,
                metadata_=context_metadata,
            )
        )

        # Link OCR report back on the Media metadata_json
        existing_meta = dict(media.metadata_json) if isinstance(media.metadata_json, dict) else {}
        existing_meta["ocr_report_id"] = str(report_row.report_id)
        existing_meta["ocr_json_path"] = rel_json_path
        media.metadata_json = existing_meta

        db.commit()
        db.refresh(report_row)

        logger.info(
            "OCR persisted for media=%s report_id=%s (entities=%d, review=%d, checks=%d)",
            media.id,
            report_row.report_id,
            len(intel_report.entities),
            len(intel_report.review_queue_items),
            len(intel_report.compliance_checks),
        )

        return {
            "report_id": str(report_row.report_id),
            "media_id": str(media.id),
            "inspection_id": str(media.inspection_id),
            "site_id": resolved_site_id,
            "json_path": rel_json_path,
            "full_text": raw_full_text,
            "translated_text": translated_text,
            "is_translated": is_translated,
            "entities_count": len(intel_report.entities),
            "review_queue_count": len(intel_report.review_queue_items),
            "compliance_checks_count": len(intel_report.compliance_checks),
            "ocr_json": report_json,
        }
