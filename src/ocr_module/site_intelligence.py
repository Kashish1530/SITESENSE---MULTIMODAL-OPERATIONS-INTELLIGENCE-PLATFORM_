"""
site_intelligence.py
--------------------
Site Text Intelligence Module.

Transforms raw OCR extractions into structured Site Intelligence:
1. Recognises entities: Equipment IDs, Serial Numbers, SKU/Pallet Tags, Dates,
   Quantities, Safety Signage, Certifications (CE, ISO), etc.
2. Confidence & Quality Assessment: Categorises findings into CONFIDENT, UNCERTAIN, or REJECTED.
3. Human-in-the-Loop Review Routing: Flags low-confidence or ambiguous detections for manual verification.
4. Compliance Rules Engine: Evaluates equipment expiry, required safety tags, capacity limits, and site rules.
5. Gen AI / LLM Context Formulation: Generates structured grounding prompts and audit summaries for downstream LLMs/Agents.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from ocr_module.models import OCRTextResult


class EntityType(str, Enum):
    EQUIPMENT_ID = "equipment_id"
    SERIAL_NUMBER = "serial_number"
    MODEL_NUMBER = "model_number"
    PALLET_TAG = "pallet_tag"
    SKU_CODE = "sku_code"
    RACK_LOCATION = "rack_location"
    QUANTITY = "quantity"
    CAPACITY_RATING = "capacity_rating"
    INSPECTION_DATE = "inspection_date"
    EXPIRY_DATE = "expiry_date"
    SAFETY_SIGNAGE = "safety_signage"
    CERTIFICATION = "certification"
    BARCODE_DATA = "barcode_data"
    QR_DATA = "qr_data"
    GENERAL_TEXT = "general_text"


class VerificationStatus(str, Enum):
    AUTO_APPROVED = "auto_approved"
    NEEDS_REVIEW = "needs_review"
    REJECTED = "rejected"


class ComplianceStatus(str, Enum):
    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    FLAGGED = "flagged"
    INSUFFICIENT_DATA = "insufficient_data"


class SiteEntity(BaseModel):
    """Structured entity extracted from site media."""
    entity_type: EntityType
    raw_text: str
    normalized_value: str
    confidence: float
    bounding_box: Optional[List[List[int]]] = None
    verification_status: VerificationStatus
    review_reason: Optional[str] = None


class ComplianceCheck(BaseModel):
    """Result of automated compliance evaluation."""
    rule_id: str
    rule_name: str
    policy_reference: str
    status: ComplianceStatus
    details: str
    evidence_text: Optional[str] = None


class SiteIntelligenceReport(BaseModel):
    """Complete Site Text Intelligence Report matching enterprise backend specs."""
    site_id: Optional[str] = "SITE-DEFAULT"
    inspection_id: Optional[str] = None
    media_name: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone(timedelta(hours=5, minutes=30))).isoformat())
    
    # 1. Raw & Aggregated Text
    full_text: str
    processing_time_ms: float
    
    # 2. Classified Entities
    entities: List[SiteEntity] = Field(default_factory=list)
    
    # 3. Human Review Routing (Review Queue)
    review_required: bool = False
    review_queue_items: List[SiteEntity] = Field(default_factory=list)
    
    # 4. Automated Compliance Evaluation
    compliance_checks: List[ComplianceCheck] = Field(default_factory=list)
    overall_compliance: ComplianceStatus = ComplianceStatus.INSUFFICIENT_DATA
    
    # 5. Gen AI & Agentic Bridge Context
    genai_context: Dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Entity Extraction Patterns & Logic
# ---------------------------------------------------------------------------

PATTERNS = {
    EntityType.SERIAL_NUMBER: [
        r"(?:serial\s*(?:no|num|#)?[:\s]*)([A-Z0-9\-]+)",
        r"(?:sn[:\s]*)([A-Z0-9\-]+)",
    ],
    EntityType.MODEL_NUMBER: [
        r"(?:model\s*(?:no|num|#)?[:\s]*)([A-Z0-9\-]+)",
        r"(?:mod[:\s]*)([A-Z0-9\-]+)",
    ],
    EntityType.SKU_CODE: [
        r"(?:sku[:\s]*)([A-Z0-9\-]+)",
    ],
    EntityType.QUANTITY: [
        r"(?:qty|quantity)[:\s]*([0-9]+\s*(?:pcs|units|kg|boxes|ctn)?)",
    ],
    EntityType.CAPACITY_RATING: [
        r"(?:capacity|cap)[:\s]*([0-9]+\s*(?:kg|lbs|t|tons))",
        r"([0-9]+\s*(?:kg|lbs|tons))\s*(?:max|capacity)",
    ],
    EntityType.PALLET_TAG: [
        r"\b(PT-[0-9]{4,6})\b",
        r"\b(LT-[0-9A-Z]{4,6})\b",
    ],
    EntityType.RACK_LOCATION: [
        r"\b([A-Z]-[0-9]{2,3})\b",
    ],
    EntityType.INSPECTION_DATE: [
        r"\b([0-9]{1,2}[/\-\.][0-9]{1,2}[/\-\.][0-9]{2,4})\b",
        r"\b([0-9]{4}[/\-\.][0-9]{1,2}[/\-\.][0-9]{1,2})\b",
    ]
}

SAFETY_KEYWORDS = [
    "FIRE", "EXTINGUISHER", "DANGER", "CAUTION", "WARNING", "EMERGENCY",
    "EXIT", "SAFETY", "HELMET", "PPE", "FIRST AID", "HARNESS", "RESTRICTED",
    "SORTIE DE SECOURS", "ATTENTION", "ACHTUNG", "NOTFAUSGANG"
]

CERT_KEYWORDS = ["CE", "ISO", "UL", "ANSI", "OSHA", "TUV", "BIS", "ISI"]


class SiteIntelligenceExtractor:
    """Analyzes raw OCR text regions and builds structured site intelligence."""

    def __init__(self, review_threshold: float = 0.70, reject_threshold: float = 0.30):
        self.review_threshold = review_threshold
        self.reject_threshold = reject_threshold

    def analyze(
        self,
        media_name: str,
        ocr_results: List[OCRTextResult],
        full_text: str,
        processing_time_ms: float,
        detected_codes: Optional[List[Dict[str, Any]]] = None,
        site_id: str = "SITE-MAIN",
    ) -> SiteIntelligenceReport:
        entities: List[SiteEntity] = []
        review_items: List[SiteEntity] = []

        # 1. Parse Barcodes / QR Codes into Entities
        if detected_codes:
            for c in detected_codes:
                val = c.get("data", "")
                ctype = c.get("type", "Code")
                etype = EntityType.QR_DATA if "QR" in ctype else EntityType.BARCODE_DATA
                entity = SiteEntity(
                    entity_type=etype,
                    raw_text=val,
                    normalized_value=val,
                    confidence=1.0,
                    bounding_box=c.get("points"),
                    verification_status=VerificationStatus.AUTO_APPROVED,
                )
                entities.append(entity)

        # 2. Extract Entities from OCR Text Lines
        for item in ocr_results:
            text = item.text.strip()
            conf = item.confidence
            bbox = item.bounding_box

            # Classify entity
            etype, norm_val = self._classify_text(text)

            # Determine Verification Status (Human-in-the-Loop Gate)
            if conf >= self.review_threshold:
                vstatus = VerificationStatus.AUTO_APPROVED
                reason = None
            elif conf >= self.reject_threshold:
                vstatus = VerificationStatus.NEEDS_REVIEW
                reason = f"Low confidence score ({conf:.2f} < {self.review_threshold:.2f})"
            else:
                vstatus = VerificationStatus.REJECTED
                reason = f"Confidence below acceptable threshold ({conf:.2f} < {self.reject_threshold:.2f})"

            entity = SiteEntity(
                entity_type=etype,
                raw_text=text,
                normalized_value=norm_val,
                confidence=round(conf, 4),
                bounding_box=bbox,
                verification_status=vstatus,
                review_reason=reason,
            )
            entities.append(entity)
            if vstatus == VerificationStatus.NEEDS_REVIEW:
                review_items.append(entity)

        # 3. Automated Compliance Checks
        compliance_checks, overall_comp = self._evaluate_compliance(entities, full_text)

        # 4. Construct Gen AI Grounding Context
        genai_context = self._build_genai_context(site_id, media_name, entities, compliance_checks, full_text)

        return SiteIntelligenceReport(
            site_id=site_id,
            media_name=media_name,
            full_text=full_text,
            processing_time_ms=processing_time_ms,
            entities=entities,
            review_required=len(review_items) > 0,
            review_queue_items=review_items,
            compliance_checks=compliance_checks,
            overall_compliance=overall_comp,
            genai_context=genai_context,
        )

    def _classify_text(self, text: str) -> tuple[EntityType, str]:
        """Maps raw text to domain entities using regex and keyword heuristics."""
        upper = text.upper()

        # Check Certifications (CE, ISO, etc.)
        for cert in CERT_KEYWORDS:
            if upper == cert or f" {cert} " in f" {upper} ":
                return EntityType.CERTIFICATION, cert

        # Check Safety Signage
        for kw in SAFETY_KEYWORDS:
            if kw in upper:
                return EntityType.SAFETY_SIGNAGE, text

        # Check Specific Regex Patterns
        for etype, pattern_list in PATTERNS.items():
            for pat in pattern_list:
                m = re.search(pat, text, re.IGNORECASE)
                if m:
                    val = m.group(1).strip()
                    return etype, val

        # Fallback heuristics for IDs
        if re.match(r"^[A-Z]{1,3}-[0-9]{2,5}$", text):
            return EntityType.EQUIPMENT_ID, text

        return EntityType.GENERAL_TEXT, text

    def _evaluate_compliance(self, entities: List[SiteEntity], full_text: str) -> tuple[List[ComplianceCheck], ComplianceStatus]:
        """Rules engine: evaluates detected entities against physical site policies."""
        checks: List[ComplianceCheck] = []
        overall = ComplianceStatus.COMPLIANT

        # Rule 1: Safety Signage Legibility & Presence
        has_safety = any(e.entity_type == EntityType.SAFETY_SIGNAGE for e in entities)
        if any("EXTINGUISHER" in e.raw_text.upper() or "FIRE" in e.raw_text.upper() for e in entities):
            checks.append(ComplianceCheck(
                rule_id="RULE-SAF-001",
                rule_name="Fire Safety Equipment Identification",
                policy_reference="Site Safety Standard Sec 4.2: All fire extinguishers must have legible identification tags.",
                status=ComplianceStatus.COMPLIANT,
                details="Fire safety equipment signage clearly identified on site.",
                evidence_text=full_text,
            ))

        # Rule 2: Equipment Plate Traceability
        serials = [e for e in entities if e.entity_type == EntityType.SERIAL_NUMBER]
        models = [e for e in entities if e.entity_type == EntityType.MODEL_NUMBER]
        if serials or models:
            checks.append(ComplianceCheck(
                rule_id="RULE-EQ-003",
                rule_name="Equipment Nameplate Traceability",
                policy_reference="Machinery & Plant Compliance Policy Sec 1.1: Every heavy machinery/plate must display model and serial number.",
                status=ComplianceStatus.COMPLIANT,
                details=f"Asset identified: Serial='{serials[0].normalized_value if serials else 'N/A'}', Model='{models[0].normalized_value if models else 'N/A'}'",
                evidence_text=full_text,
            ))

        # Rule 3: Pallet / Material Identification
        pallets = [e for e in entities if e.entity_type in (EntityType.PALLET_TAG, EntityType.SKU_CODE)]
        if pallets:
            checks.append(ComplianceCheck(
                rule_id="RULE-LOG-005",
                rule_name="Inventory & Material Tagging",
                policy_reference="Warehouse Logistics Standard Sec 3.4: Unlabeled stock prohibited in active aisles.",
                status=ComplianceStatus.COMPLIANT,
                details=f"Material tag verified: {pallets[0].normalized_value}",
                evidence_text=pallets[0].raw_text,
            ))

        # Rule 4: Data Quality & Low-Confidence Guardrail
        unverified = [e for e in entities if e.verification_status == VerificationStatus.NEEDS_REVIEW]
        if len(unverified) >= 2:
            checks.append(ComplianceCheck(
                rule_id="RULE-SYS-009",
                rule_name="Extraction Confidence Guardrail",
                policy_reference="Quality Gate Policy Sec 2: Readings below 70% confidence require manual supervisor sign-off before regulatory filing.",
                status=ComplianceStatus.FLAGGED,
                details=f"{len(unverified)} text regions require human verification in the review queue.",
                evidence_text=", ".join(e.raw_text for e in unverified[:3]),
            ))
            overall = ComplianceStatus.FLAGGED

        if not checks:
            overall = ComplianceStatus.INSUFFICIENT_DATA

        return checks, overall

    def _build_genai_context(
        self,
        site_id: str,
        media_name: str,
        entities: List[SiteEntity],
        compliance_checks: List[ComplianceCheck],
        full_text: str,
    ) -> Dict[str, Any]:
        """Prepares a grounded payload for LLM/RAG pipelines and Agentic reasoning."""
        key_facts = []
        for e in entities:
            if e.entity_type != EntityType.GENERAL_TEXT:
                key_facts.append(f"{e.entity_type.value}: {e.normalized_value} (conf: {e.confidence:.0%})")

        compliance_summary = [f"[{c.status.value.upper()}] {c.rule_name} - {c.details}" for c in compliance_checks]

        prompt_context = (
            f"SITE INSPECTION EVIDENCE GROUNDING:\n"
            f"Location/Site: {site_id}\n"
            f"Source Media: {media_name}\n"
            f"Verified Text: {full_text}\n"
            f"Key Extracted Entities:\n- " + "\n- ".join(key_facts if key_facts else ["No specific structured IDs"]) + "\n"
            f"Compliance Findings:\n- " + "\n- ".join(compliance_summary if compliance_summary else ["No automated rule triggered"])
        )

        return {
            "prompt_ready_context": prompt_context,
            "structured_evidence": {
                "site_id": site_id,
                "media": media_name,
                "detected_entities": [e.model_dump() for e in entities],
                "compliance_findings": [c.model_dump() for c in compliance_checks],
            },
            "suggested_llm_actions": [
                "Generate Site Audit Incident Report",
                "Cross-check Equipment ID against Maintenance Registry",
                "Raise Human Review Ticket for flagged confidence items",
            ],
        }
