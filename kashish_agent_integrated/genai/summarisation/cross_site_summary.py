"""
SITESENSE - Grounded Cross-Site Operations Summariser (Feature 3.8)
Aggregates and summarises recurring compliance failures across facilities,
identifying worst-trending sites and top rule violations grounded strictly
in Neon DB empirical queries rather than hallucinated generation.
"""

import os
from pathlib import Path
from typing import Dict, Any, List
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")


def generate_cross_site_summary(limit_inspections: int = 20) -> Dict[str, Any]:
    """
    Extracts empirical ground-truth figures across the latest inspections
    and generates a strictly grounded management operational summary.
    """
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        return {"success": False, "error": "DATABASE_URL not set."}

    conn = psycopg2.connect(db_url)
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # 1. Total inspections analyzed
    cur.execute("""
        SELECT i.id, i.created_at, i.status, s.id as site_id, s.name as site_name
        FROM inspections i
        JOIN sites s ON i.site_id = s.id
        ORDER BY i.created_at DESC
        LIMIT %s;
    """, (limit_inspections,))
    inspections = cur.fetchall()

    if not inspections:
        cur.close()
        conn.close()
        return {"success": False, "error": "No inspections found in database."}

    inspection_ids = [str(i["id"]) for i in inspections]

    # 2. Findings across these inspections
    cur.execute("""
        SELECT f.id, f.inspection_id, f.status, r.id as rule_id, r.name as rule_name, r.policy_ref, i.site_id, s.name as site_name
        FROM findings f
        JOIN rules r ON f.rule_id = r.id
        JOIN inspections i ON f.inspection_id = i.id
        JOIN sites s ON i.site_id = s.id
        WHERE f.inspection_id::text = ANY(%s);
    """, (inspection_ids,))
    findings = cur.fetchall()

    cur.close()
    conn.close()

    # 3. Compute empirical statistics
    total_inspections = len(inspections)
    total_findings = len(findings)
    total_passed = sum(1 for f in findings if f["status"] == "pass")
    total_failed = sum(1 for f in findings if f["status"] == "fail")

    # Group by rule failures
    rule_failure_counts: Dict[str, int] = {}
    for f in findings:
        if f["status"] == "fail":
            r_name = f"{f['rule_name']} ({f['policy_ref']})"
            rule_failure_counts[r_name] = rule_failure_counts.get(r_name, 0) + 1

    sorted_failing_rules = sorted(rule_failure_counts.items(), key=lambda x: x[1], reverse=True)
    top_failing_rule = sorted_failing_rules[0][0] if sorted_failing_rules else "None"

    # Group by site failure rates
    site_stats: Dict[str, Dict[str, int]] = {}
    for f in findings:
        s_name = f["site_name"]
        if s_name not in site_stats:
            site_stats[s_name] = {"total": 0, "failed": 0, "passed": 0}
        site_stats[s_name]["total"] += 1
        if f["status"] == "fail":
            site_stats[s_name]["failed"] += 1
        else:
            site_stats[s_name]["passed"] += 1

    site_failure_rates = {
        s: round((st["failed"] / st["total"] * 100), 1) if st["total"] > 0 else 0.0
        for s, st in site_stats.items()
    }
    worst_site = max(site_failure_rates.items(), key=lambda x: x[1])[0] if site_failure_rates else "None"

    overall_pass_rate = round((total_passed / total_findings * 100), 1) if total_findings > 0 else 100.0

    # 4. Synthesize grounded executive report (figures match database queries exactly)
    summary_markdown = f"""
# SiteSense Cross-Site Operations Intelligence Summary
**Analyzed Period:** Latest {total_inspections} Inspections across Active Facilities
**Overall Compliance Pass Rate:** {overall_pass_rate}% ({total_passed}/{total_findings} checks passed)

## 1. Facility Performance & Worst Trending Site
- **Highest Risk / Worst Trending Facility:** **{worst_site}** (Failure rate: {site_failure_rates.get(worst_site, 0)}%)
{chr(10).join([f"- **{site}**: {st['failed']} violations out of {st['total']} evaluated rules ({site_failure_rates[site]}% breach rate)" for site, st in site_stats.items()])}

## 2. Most Frequently Breached Safety Rules
- **Top Violating Standard:** **{top_failing_rule}** ({sorted_failing_rules[0][1] if sorted_failing_rules else 0} infractions recorded)
{chr(10).join([f"- {r}: {cnt} recurring violations" for r, cnt in sorted_failing_rules[:3]]) if sorted_failing_rules else "- No active rule breaches recorded across evaluated sample."}

## 3. Recommended Management Actions
1. Deploy targeted safety retraining at **{worst_site}**.
2. Audit contractor and operator compliance regarding **{top_failing_rule}**.
3. Require high-risk areas to submit daily visual inspection logs.
""".strip()

    return {
        "success": True,
        "inspections_analyzed": total_inspections,
        "total_checks": total_findings,
        "total_passed": total_passed,
        "total_failed": total_failed,
        "overall_pass_rate": f"{overall_pass_rate}%",
        "worst_trending_site": worst_site,
        "top_failing_rule": top_failing_rule,
        "site_breakdown": site_stats,
        "rule_breakdown": rule_failure_counts,
        "summary_markdown": summary_markdown
    }
