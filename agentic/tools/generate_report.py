"""
Report generation tool for the SiteSense agent.

Assembles structured inspection findings, policy rules, linked evidence,
and extracted document data into a formatted report, exportable as PDF.
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional
import psycopg2
from psycopg2.extras import RealDictCursor
import fitz # PyMuPDF

from agentic.tools.registry import registry
from agentic.tools.query_database import get_db_url

REPORT_OUTPUT_DIR = Path("storage/reports")
REPORT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def export_report_to_pdf(report_data: Dict[str, Any], output_path: Path) -> str:
    """Renders structured inspection report data into a clean PDF document using PyMuPDF."""
    doc = fitz.open()
    page = doc.new_page(width=595, height=842) # A4 format

    # Colors
    c_primary = (0.05, 0.2, 0.45)
    c_dark = (0.1, 0.1, 0.15)
    c_gray = (0.4, 0.45, 0.5)
    c_green = (0.1, 0.6, 0.2)
    c_red = (0.8, 0.1, 0.1)

    y = 50

    # Header Title
    page.insert_text(fitz.Point(50, y), "SITESENSE OPERATIONS INTELLIGENCE", fontsize=16, fontname="helv", color=c_primary)
    y += 20
    page.insert_text(fitz.Point(50, y), f"Facility Compliance & Safety Audit Report — {report_data['report_id']}", fontsize=11, fontname="helv", color=c_gray)
    y += 15
    page.draw_line(fitz.Point(50, y), fitz.Point(545, y), color=c_gray, width=0.8)
    y += 25

    # Facility Details Table
    page.insert_text(fitz.Point(50, y), f"Site: {report_data['site']}", fontsize=10, fontname="helv", color=c_dark)
    page.insert_text(fitz.Point(320, y), f"Location: {report_data.get('location', 'N/A')}", fontsize=10, fontname="helv", color=c_dark)
    y += 18
    page.insert_text(fitz.Point(50, y), f"Inspector: {report_data.get('inspector', 'Auditor')}", fontsize=10, fontname="helv", color=c_dark)
    page.insert_text(fitz.Point(320, y), f"Inspection Date: {report_data['inspection_date']}", fontsize=10, fontname="helv", color=c_dark)
    y += 25

    # Executive Summary Card
    summ = report_data["summary"]
    page.draw_rect(fitz.Rect(50, y, 545, y + 45), fill=(0.95, 0.97, 1.0), color=c_primary, width=0.5)
    y += 18
    summary_text = (
        f"Compliance Score: {summ['compliance_score']}  |  "
        f"Total Checks: {summ['total_checks']}  |  "
        f"Passed: {summ['passed']}  |  "
        f"Failed: {summ['failed']}  |  "
        f"Review: {summ['needs_review']}"
    )
    page.insert_text(fitz.Point(60, y), summary_text, fontsize=10, fontname="helv", color=c_primary)
    y += 45

    # Section: Rule Evaluation & Findings
    page.insert_text(fitz.Point(50, y), "RULE COMPLIANCE FINDINGS & EVIDENCE", fontsize=12, fontname="helv", color=c_primary)
    y += 10
    page.draw_line(fitz.Point(50, y), fitz.Point(545, y), color=c_gray, width=0.5)
    y += 20

    for f in report_data.get("findings_detail", []):
        status = f.get("status", "pass").upper()
        status_color = c_green if status == "PASS" else (c_red if status == "FAIL" else c_gray)

        # Rule Name & Status badge
        page.insert_text(fitz.Point(50, y), f"[{status}]", fontsize=9, fontname="helv", color=status_color)
        page.insert_text(fitz.Point(100, y), f"{f.get('rule_name', 'Rule')} ({f.get('policy_ref', 'Policy')})", fontsize=9, fontname="helv", color=c_dark)
        y += 14

        # Evidence
        evidence = f.get("evidence_ids") or "No direct violation"
        page.insert_text(fitz.Point(100, y), f"Evidence: {evidence} | Desc: {f.get('description', '')[:70]}", fontsize=8, fontname="helv", color=c_gray)
        y += 20

        if y > 750: # Page overflow protection
            page = doc.new_page(width=595, height=842)
            y = 50

    # Recommended Actions
    y += 15
    page.insert_text(fitz.Point(50, y), "RECOMMENDED REMEDIATION ACTIONS", fontsize=11, fontname="helv", color=c_primary)
    y += 18
    if summ['failed'] > 0:
        page.insert_text(fitz.Point(60, y), "1. Immediate corrective maintenance tickets proposed for all failed safety rules.", fontsize=9, fontname="helv", color=c_dark)
        y += 14
        page.insert_text(fitz.Point(60, y), "2. Re-inspection required within 48 hours for PPE / forklift corridor compliance.", fontsize=9, fontname="helv", color=c_dark)
    else:
        page.insert_text(fitz.Point(60, y), "All operations meet governing company policy standards. No remediation tickets required.", fontsize=9, fontname="helv", color=c_dark)

    doc.save(str(output_path))
    doc.close()
    return str(output_path)


@registry.register(
    name="generate_report",
    description="Generate a comprehensive inspection compliance report for a site inspection with linked evidence and rule evaluations, exportable as PDF.",
    parameters={
        "type": "object",
        "properties": {
            "inspection_id": {
                "type": "string",
                "description": "The UUID of the completed inspection to generate a report for."
            },
            "export_pdf": {
                "type": "boolean",
                "description": "If true, exports and renders a formal PDF report document."
            }
        },
        "required": ["inspection_id"]
    }
)
def generate_report(inspection_id: str, export_pdf: bool = True) -> Dict[str, Any]:
    db_url = get_db_url()
    if not db_url:
        return {"success": False, "error": "DATABASE_URL not configured."}

    try:
        conn = psycopg2.connect(db_url)
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # 1. Inspection details
        cur.execute("""
            SELECT i.id, i.created_at, i.status, s.name AS site_name, s.location, u.name AS inspector
            FROM inspections i
            JOIN sites s ON i.site_id = s.id
            LEFT JOIN users u ON i.user_id = u.id
            WHERE i.id::text = %s;
        """, (inspection_id,))
        insp = cur.fetchone()
        if not insp:
            cur.close()
            conn.close()
            return {"success": False, "error": f"Inspection '{inspection_id}' not found."}

        # 2. Findings & Rules
        cur.execute("""
            SELECT f.id AS finding_id, f.status, f.evidence_ids, r.name AS rule_name, r.policy_ref, r.description
            FROM findings f
            JOIN rules r ON f.rule_id = r.id
            WHERE f.inspection_id::text = %s;
        """, (inspection_id,))
        findings = cur.fetchall()

        # 3. Linked Document Extractions (Feature 3.7 integration)
        cur.execute("""
            SELECT e.field_name, e.value, e.confidence
            FROM extractions e
            JOIN media m ON e.media_id = m.id
            WHERE m.inspection_id::text = %s
            LIMIT 10;
        """, (inspection_id,))
        extractions = cur.fetchall()

        cur.close()
        conn.close()

        total = len(findings)
        passed = sum(1 for f in findings if f["status"] == "pass")
        failed = sum(1 for f in findings if f["status"] == "fail")
        reviews = sum(1 for f in findings if f["status"] == "review")

        pass_rate = f"{(passed / total * 100):.1f}%" if total > 0 else "N/A"
        report_id = f"REP-{inspection_id[:8].upper()}"

        report_payload = {
            "success": True,
            "report_id": report_id,
            "site": insp["site_name"],
            "location": insp["location"],
            "inspector": insp["inspector"] or "Certified Lead Auditor",
            "inspection_date": str(insp["created_at"])[:19],
            "summary": {
                "total_checks": total,
                "passed": passed,
                "failed": failed,
                "needs_review": reviews,
                "compliance_score": pass_rate
            },
            "findings_detail": findings,
            "document_extractions": extractions,
            "recommended_actions": [
                "Address failed findings with proposed remediation tickets",
                "Review low-confidence document extractions in review queue"
            ] if failed > 0 else ["Maintain current facility compliance standards"]
        }

        # PDF Export
        if export_pdf:
            pdf_filename = f"{report_id}.pdf"
            pdf_path = REPORT_OUTPUT_DIR / pdf_filename
            export_report_to_pdf(report_payload, pdf_path)
            report_payload["pdf_path"] = str(pdf_path)
            report_payload["download_url"] = f"/reports/{pdf_filename}"

        return report_payload

    except Exception as e:
        return {"success": False, "error": str(e)}
