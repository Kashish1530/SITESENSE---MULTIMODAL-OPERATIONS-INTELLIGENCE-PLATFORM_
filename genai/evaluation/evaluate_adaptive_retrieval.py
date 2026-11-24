
import json
import statistics
from collections import Counter
from pathlib import Path

from genai.evaluation.evaluate_retrieval import (
    load_dataset,
    calculate_metrics,
    deduplicate_results,
)
from genai.retrieval.hybrid_search import HybridSearch


# ==========================================================
# CONFIGURATION
# ==========================================================

BASE_DIR = Path(__file__).resolve().parent

BASELINE_FILE = (
    BASE_DIR / "retrieval_evaluation_minilm_l12_baseline.json"
)

OUTPUT_FILE = (
    BASE_DIR / "adaptive_retrieval_results.json"
)

TOP_K = 20

METRIC_NAMES = [
    "Recall@5",
    "Recall@10",
    "MRR",
    "nDCG@5",
    "nDCG@10",
]


# ==========================================================
# VALIDATION AND HELPER FUNCTIONS
# ==========================================================

def load_baseline():

    if not BASELINE_FILE.exists():
        raise FileNotFoundError(
            f"Protected baseline not found: {BASELINE_FILE}"
        )

    with open(BASELINE_FILE, "r", encoding="utf-8") as file:
        baseline = json.load(file)

    if "results" not in baseline:
        raise ValueError(
            "Baseline JSON does not contain a results field."
        )

    baseline_by_id = {}

    for item in baseline["results"]:

        query_id = item.get("query_id")

        if not query_id:
            raise ValueError(
                "A baseline result is missing query_id."
            )

        if query_id in baseline_by_id:
            raise ValueError(
                f"Duplicate baseline query ID: {query_id}"
            )

        methods = item.get("methods", {})

        if "Hybrid_Reranked" not in methods:
            raise ValueError(
                f"Hybrid_Reranked missing for {query_id}"
            )

        ranked_ids = methods["Hybrid_Reranked"].get(
            "ranked_chunk_ids"
        )

        if not isinstance(ranked_ids, list):
            raise ValueError(
                f"Invalid ranked_chunk_ids for {query_id}"
            )

        baseline_by_id[query_id] = item

    return baseline, baseline_by_id


def calculate_macro_average(query_results):

    if not query_results:
        raise ValueError("Cannot average an empty result set.")

    averages = {}

    for metric in METRIC_NAMES:

        values = [
            item["metrics"][metric]
            for item in query_results
        ]

        averages[metric] = round(
            sum(values) / len(values),
            4,
        )

    return averages


def calculate_baseline_metrics(
    baseline_item,
    relevant_chunks,
):

    ranked_ids = baseline_item["methods"][
        "Hybrid_Reranked"
    ]["ranked_chunk_ids"]

    ranked_results = [
        {"chunk_id": chunk_id}
        for chunk_id in ranked_ids
    ]

    return calculate_metrics(
        ranked_results,
        relevant_chunks,
    )


def print_metrics(title, metrics):

    print("\n" + title)
    print("-" * 55)

    for metric in METRIC_NAMES:

        print(
            f"{metric:<15}: {metrics[metric]:.4f}"
        )


# ==========================================================
# MAIN EVALUATION
# ==========================================================

def main():

    print("\n" + "=" * 65)
    print(" SITESENSE ADAPTIVE RETRIEVAL EVALUATION")
    print("=" * 65)

    # ------------------------------------------------------
    # LOAD DATASET
    # ------------------------------------------------------

    dataset = load_dataset()

    print("\nDataset:", dataset["dataset_name"])
    print("Total queries:", len(dataset["queries"]))
    print("Top K:", TOP_K)

    # ------------------------------------------------------
    # LOAD PROTECTED BASELINE
    # ------------------------------------------------------

    print("\nLoading protected MiniLM-L12 baseline...")

    baseline, baseline_by_id = load_baseline()

    dataset_ids = {
        item["query_id"]
        for item in dataset["queries"]
    }

    baseline_ids = set(baseline_by_id.keys())

    if dataset_ids != baseline_ids:

        missing = sorted(dataset_ids - baseline_ids)
        unexpected = sorted(baseline_ids - dataset_ids)

        raise ValueError(
            "Dataset and baseline query IDs do not match.\n"
            f"Missing from baseline: {missing}\n"
            f"Unexpected in baseline: {unexpected}"
        )

    print("Baseline queries verified:", len(baseline_ids))

    # ------------------------------------------------------
    # INITIALIZE ADAPTIVE RETRIEVAL
    # ------------------------------------------------------

    print("\nInitializing adaptive retrieval engine...")

    search_engine = HybridSearch()

    # ------------------------------------------------------
    # EVALUATE QUERIES
    # ------------------------------------------------------

    adaptive_results = []
    baseline_query_metrics = []

    strategy_counts = Counter()
    latency_values = []

    for query_number, item in enumerate(
        dataset["queries"],
        start=1,
    ):

        query_id = item["query_id"]
        query = item["query"]
        relevant_chunks = item["relevant_chunks"]

        print("\n" + "=" * 65)
        print(f"QUERY {query_number}: {query_id}")
        print("Question:", query)
        print("=" * 65)

        # --------------------------------------------------
        # 1. RUN AUTOMATIC ADAPTIVE RETRIEVAL
        # --------------------------------------------------

        # Do not pass strategy.
        # QueryAnalyzer must select it automatically.

        results = search_engine.search(
            query=query,
            top_k=TOP_K,
        )

        results = deduplicate_results(results)

        if not results:
            raise RuntimeError(
                f"No results returned for {query_id}"
            )

        # --------------------------------------------------
        # 2. EXTRACT TRACE METADATA
        # --------------------------------------------------

        first_result = results[0]

        selected_strategy = first_result[
            "retrieval_strategy"
        ]

        query_variants = first_result[
            "query_variants"
        ]

        latency_ms = first_result[
            "retrieval_latency_ms"
        ]

        source_count = first_result[
            "retrieval_source_count"
        ]

        candidate_count = first_result[
            "fusion_candidate_count"
        ]

        strategy_counts[selected_strategy] += 1
        latency_values.append(latency_ms)

        # --------------------------------------------------
        # 3. CALCULATE ADAPTIVE METRICS
        # --------------------------------------------------

        adaptive_metrics = calculate_metrics(
            results,
            relevant_chunks,
        )

        # --------------------------------------------------
        # 4. CALCULATE BASELINE METRICS
        # --------------------------------------------------

        baseline_item = baseline_by_id[query_id]

        baseline_metrics = calculate_baseline_metrics(
            baseline_item,
            relevant_chunks,
        )

        baseline_query_metrics.append({
            "query_id": query_id,
            "metrics": baseline_metrics,
        })

        # --------------------------------------------------
        # 5. CALCULATE PER-QUERY DELTA
        # --------------------------------------------------

        metric_delta = {}

        for metric in METRIC_NAMES:

            metric_delta[metric] = round(
                adaptive_metrics[metric]
                - baseline_metrics[metric],
                4,
            )

        # --------------------------------------------------
        # 6. SAVE QUERY RESULT
        # --------------------------------------------------

        query_result = {
            "query_id": query_id,
            "query": query,
            "relevant_chunks": relevant_chunks,

            "adaptive": {
                "strategy": selected_strategy,
                "query_variants": query_variants,
                "query_variant_count": len(query_variants),
                "retrieval_source_count": source_count,
                "fusion_candidate_count": candidate_count,
                "latency_ms": latency_ms,
                "metrics": adaptive_metrics,
                "ranked_chunk_ids": [
                    result["chunk_id"]
                    for result in results
                ],
            },

            "baseline": {
                "strategy": "HYBRID_RERANKED",
                "metrics": baseline_metrics,
                "ranked_chunk_ids": baseline_item[
                    "methods"
                ]["Hybrid_Reranked"]["ranked_chunk_ids"],
            },

            "metric_delta": metric_delta,
        }

        adaptive_results.append(query_result)

        # --------------------------------------------------
        # 7. PRINT QUERY SUMMARY
        # --------------------------------------------------

        print("\nSelected strategy:", selected_strategy)
        print("Generated variants:", len(query_variants))
        print("Retrieval sources:", source_count)
        print("Fusion candidates:", candidate_count)
        print("Latency:", latency_ms, "ms")

        print_metrics(
            "ADAPTIVE RETRIEVAL",
            adaptive_metrics,
        )

        print_metrics(
            "MINILM-L12 BASELINE",
            baseline_metrics,
        )

        print("\nMETRIC DELTA (ADAPTIVE - BASELINE)")
        print("-" * 55)

        for metric, delta in metric_delta.items():

            print(
                f"{metric:<15}: {delta:+.4f}"
            )

    # ======================================================
    # AGGREGATE RESULTS
    # ======================================================

    adaptive_average = calculate_macro_average(
        [
            {
                "metrics": item["adaptive"]["metrics"]
            }
            for item in adaptive_results
        ]
    )

    baseline_average = calculate_macro_average(
        baseline_query_metrics
    )

    average_delta = {}

    for metric in METRIC_NAMES:

        average_delta[metric] = round(
            adaptive_average[metric]
            - baseline_average[metric],
            4,
        )

    # ======================================================
    # LATENCY SUMMARY
    # ======================================================

    latency_summary = {
        "average_ms": round(
            statistics.mean(latency_values),
            2,
        ),
        "median_ms": round(
            statistics.median(latency_values),
            2,
        ),
        "minimum_ms": round(
            min(latency_values),
            2,
        ),
        "maximum_ms": round(
            max(latency_values),
            2,
        ),
    }

    # ======================================================
    # STRATEGY SUMMARY
    # ======================================================

    strategy_summary = dict(strategy_counts)

    # ======================================================
    # SAVE OUTPUT
    # ======================================================

    output = {
        "dataset_name": dataset["dataset_name"],
        "dataset_version": dataset.get(
            "version",
            "unknown",
        ),
        "total_queries": len(adaptive_results),
        "top_k": TOP_K,

        "baseline_file": BASELINE_FILE.name,

        "adaptive_configuration": {
            "strategy_selection": "automatic",
            "candidate_count": 20,
            "keyword_candidate_count": 40,
            "reranker": "cross-encoder/ms-marco-MiniLM-L-12-v2",
        },

        "aggregate_comparison": {
            "baseline": baseline_average,
            "adaptive": adaptive_average,
            "delta": average_delta,
        },

        "latency_summary": latency_summary,

        "strategy_distribution": strategy_summary,

        "results": adaptive_results,
    }

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            output,
            file,
            indent=4,
            ensure_ascii=False,
        )

    # ======================================================
    # FINAL REPORT
    # ======================================================

    print("\n" + "=" * 70)
    print(" ADAPTIVE RETRIEVAL BENCHMARK COMPLETED")
    print("=" * 70)

    print_metrics(
        "MINILM-L12 BASELINE MACRO AVERAGE",
        baseline_average,
    )

    print_metrics(
        "ADAPTIVE RETRIEVAL MACRO AVERAGE",
        adaptive_average,
    )

    print("\nOVERALL METRIC DELTA")
    print("-" * 55)

    for metric, delta in average_delta.items():

        print(
            f"{metric:<15}: {delta:+.4f}"
        )

    print("\nSTRATEGY DISTRIBUTION")
    print("-" * 55)

    for strategy, count in strategy_summary.items():

        print(f"{strategy:<20}: {count}")

    print("\nLATENCY SUMMARY")
    print("-" * 55)

    for name, value in latency_summary.items():

        print(f"{name:<15}: {value} ms")

    print("\nResults saved to:")
    print(OUTPUT_FILE)

    print("\nProtected baseline was not modified.")


if __name__ == "__main__":
    main()
