
import json
from pathlib import Path

from genai.retrieval.query_analyzer import QueryAnalyzer


PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATASET_PATH = (
    PROJECT_ROOT
    / "genai"
    / "evaluation"
    / "retrieval_dataset.json"
)

OUTPUT_PATH = (
    PROJECT_ROOT
    / "genai"
    / "evaluation"
    / "query_analyzer_results.json"
)


def load_dataset():

    if not DATASET_PATH.exists():
        raise FileNotFoundError(
            f"Dataset not found: {DATASET_PATH}"
        )

    with open(DATASET_PATH, "r", encoding="utf-8") as file:
        return json.load(file)


def main():

    print("\n" + "=" * 75)
    print(" SITESENSE QUERY ANALYZER EVALUATION")
    print("=" * 75)

    dataset = load_dataset()
    analyzer = QueryAnalyzer()

    queries = dataset.get("queries", [])

    if not queries:
        raise ValueError("No queries found in evaluation dataset.")

    results = []

    strategy_counts = {
        "STANDARD": 0,
        "EXPANDED": 0,
        "KEYWORD_FOCUSED": 0,
    }

    for item in queries:

        query_id = item["query_id"]
        query = item["query"]

        analysis = analyzer.analyze(query)

        strategy = analysis["strategy"]

        strategy_counts[strategy] += 1

        result = {
            "query_id": query_id,
            **analysis,
        }

        results.append(result)

        print("\nQuery ID:", query_id)
        print("Question:", query)
        print("Strategy:", strategy)

        print(
            "Expansion signals:",
            analysis["expansion_signals"]
        )

        print(
            "Keyword signals:",
            analysis["keyword_signals"]
        )

        print("-" * 75)

    output = {
        "experiment": "query_analyzer_evaluation",
        "dataset_name": dataset.get("dataset_name"),
        "dataset_version": dataset.get("dataset_version"),
        "total_queries": len(results),
        "strategy_distribution": strategy_counts,
        "results": results,
    }

    with open(
        OUTPUT_PATH,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            output,
            file,
            indent=4,
            ensure_ascii=False
        )

    print("\n" + "=" * 75)
    print(" STRATEGY DISTRIBUTION")
    print("=" * 75)

    for strategy, count in strategy_counts.items():

        percentage = (
            count / len(results)
        ) * 100

        print(
            f"{strategy:<20}: "
            f"{count}/{len(results)} "
            f"({percentage:.1f}%)"
        )

    print("\nEvaluation completed.")
    print("Results saved to:", OUTPUT_PATH)


if __name__ == "__main__":
    main()
