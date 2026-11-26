"""
SITESENSE - Query Router Benchmark (Feature 4.3)
Acceptance Criteria:
"Routing accuracy measured on a labelled question set, reported as its own number."
"""

import sys
import json
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from agentic.router import route_query
from agentic.guardrails import check_input_guardrail

TEST_SET_PATH = PROJECT_ROOT / "evals" / "golden_sets" / "agent_test_set.json"


def evaluate_query_router():
    print("=" * 80)
    print("         SITESENSE - QUERY ROUTER ACCURACY BENCHMARK (FEATURE 4.3)")
    print("=" * 80)

    with open(TEST_SET_PATH, "r", encoding="utf-8") as f:
        test_cases = json.load(f)

    total = len(test_cases)
    correct = 0

    print(f"\nEvaluating {total} labeled test questions across routing categories...\n")

    for tc in test_cases:
        qid = tc["id"]
        q_text = tc["question"]
        expected = tc["expected_route"]
        has_img = tc.get("requires_image", False)

        # Check guardrail first for blocked route
        is_safe, _ = check_input_guardrail(q_text)
        if not is_safe:
            actual = "blocked"
            confidence = 1.0
        else:
            route_res = route_query(q_text, has_image=has_img)
            actual = route_res.get("route")
            confidence = route_res.get("confidence", 0.0)

        is_match = (actual == expected)
        if is_match:
            correct += 1
            status_tag = "[PASS]"
        else:
            status_tag = "[FAIL]"

        print(f"  {status_tag} Case {qid}: Expected '{expected}' -> Predicted '{actual}' (Conf: {confidence:.2f})")
        print(f"         Q: \"{q_text}\"")

    accuracy = (correct / total) * 100.0

    print("\n" + "-" * 80)
    print(f"ROUTING ACCURACY ON LABELLED TEST SET: {accuracy:.1f}% ({correct}/{total} correct)")
    print("-" * 80)

    assert accuracy >= 80.0, f"Router accuracy {accuracy:.1f}% below acceptable threshold!"
    print("-> ACCEPTANCE CRITERIA FOR FEATURE 4.3 PASSED!\n")
    return accuracy


if __name__ == "__main__":
    evaluate_query_router()
