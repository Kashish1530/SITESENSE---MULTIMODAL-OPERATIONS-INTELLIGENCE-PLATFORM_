 
import re
from typing import Dict


class QueryAnalyzer:
    """
    Lightweight rule-based query analyzer for SITESENSE.

    Classifies questions into three retrieval strategies:

    1. STANDARD
       Uses normal dense + BM25 hybrid retrieval.

    2. EXPANDED
       Uses multiple query formulations to improve
       candidate recall for broad or multi-concept questions.

    3. KEYWORD_FOCUSED
       Identifies terminology that may benefit from
       stronger lexical retrieval.

    This implementation is deterministic and does not
    require an external LLM API.
    """

    # --------------------------------------------------
    # CONFIGURATION
    # --------------------------------------------------

    EXPANSION_SIGNALS = [
        "and",
        "or",
        "also",
        "including",
        "investigate",
        "investigation",
        "procedure",
        "process",
        "requirements",
        "precautions",
        "responsibilities",
        "different types",
        "all steps",
        "complete process",
    ]

    KEYWORD_SIGNALS = [
        "forklift",
        "pallet jack",
        "ppe",
        "sodium hydroxide",
        "chemical",
        "chemicals",
        "electrical",
        "hazardous substance",
        "hazardous substances",
        "fire extinguisher",
        "lockout tagout",
        "near miss",
        "near misses",
        "incident report",
        "incident reporting",
        "sds",
        "msds",
    ]

    COMPLEX_INTENT_PATTERNS = [
        "reported and investigated",
        "selected and maintained",
        "storage and handling",
        "identify and assess",
        "prevent and control",
        "reporting and investigation",
        "handling and moving",
        "incidents and near misses",
    	"incident and near miss",
    	"incident reporting",
    	"near miss reporting",
    	"chemical safety",
    	"chemical handling",
	"handling chemicals",
	"handling hazardous substances",
    ]

    # --------------------------------------------------
    # INITIALIZATION
    # --------------------------------------------------

    def __init__(self):
        pass

    # --------------------------------------------------
    # QUERY ANALYSIS
    # --------------------------------------------------

    def analyze(self, query: str) -> Dict:

        if not isinstance(query, str) or not query.strip():
            raise ValueError("Query cannot be empty.")

        normalized = query.lower().strip()

        # Extract words.
        words = re.findall(
            r"\b[\w-]+\b",
            normalized
        )

        # Identify expansion signals.
        expansion_matches = [
            signal
            for signal in self.EXPANSION_SIGNALS
            if re.search(
                rf"\b{re.escape(signal)}\b",
                normalized
            )
        ]

        # Identify technical keywords.
        keyword_matches = [
            signal
            for signal in self.KEYWORD_SIGNALS
            if re.search(
                rf"\b{re.escape(signal)}\b",
                normalized
            )
        ]

        # Check for multiple concepts.
        has_multiple_concepts = (
            re.search(r"\band\b", normalized) is not None
            or re.search(r"\bor\b", normalized) is not None
        )

        # Check for known complex intents.
        has_complex_intent = any(
            pattern in normalized
            for pattern in self.COMPLEX_INTENT_PATTERNS
        )

        # --------------------------------------------------
        # RETRIEVAL STRATEGY SELECTION
        # --------------------------------------------------

        if (
            len(expansion_matches) >= 2
            or has_complex_intent
            or (
                len(words) >= 12
                and has_multiple_concepts
            )
        ):

            strategy = "EXPANDED"

        elif keyword_matches:

            strategy = "KEYWORD_FOCUSED"

        else:

            strategy = "STANDARD"

        # --------------------------------------------------
        # ANALYSIS RESULT
        # --------------------------------------------------

        return {
            "original_query": query,
            "normalized_query": normalized,
            "word_count": len(words),
            "expansion_signals": expansion_matches,
            "keyword_signals": keyword_matches,
            "has_multiple_concepts": has_multiple_concepts,
            "has_complex_intent": has_complex_intent,
            "strategy": strategy,
        }


# ------------------------------------------------------
# TESTING
# ------------------------------------------------------

def main():

    analyzer = QueryAnalyzer()

    test_queries = [

        # Q001
        "What are the safety rules for forklift operators?",

        # Q005
        "How should incidents and near misses be reported and investigated?",

        # Chemical handling
        "What is the procedure for handling sodium hydroxide?",

        # Q002
        "How should warehouse PPE be selected and maintained?",

        # Q003
        "What should workers do during an emergency evacuation?",

        # Q006
        "What precautions should workers follow when handling chemicals?",

        # Q004
        "What precautions apply to electrical work and damaged equipment?",

        # Q008
        "How should pedestrian routes be kept clear?",

        # Q007
        "How should workers safely handle and move heavy materials?",
    ]

    print("\n" + "=" * 75)
    print(" SITESENSE QUERY ANALYZER")
    print("=" * 75)

    for index, query in enumerate(test_queries, start=1):

        result = analyzer.analyze(query)

        print(f"\nQUERY {index}")
        print("-" * 75)

        print("Question:", result["original_query"])

        print("Word count:", result["word_count"])

        print(
            "Expansion signals:",
            result["expansion_signals"]
        )

        print(
            "Keyword signals:",
            result["keyword_signals"]
        )

        print(
            "Multiple concepts:",
            result["has_multiple_concepts"]
        )

        print(
            "Complex intent:",
            result["has_complex_intent"]
        )

        print(
            "Selected strategy:",
            result["strategy"]
        )

    print("\n" + "=" * 75)
    print("QUERY ANALYSIS COMPLETED")
    print("=" * 75)


if __name__ == "__main__":
    main()
