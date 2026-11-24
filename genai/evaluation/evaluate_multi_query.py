
import json
from pathlib import Path

from genai.retrieval.pgvector_search import semantic_search
from genai.retrieval.bm25_search import BM25Search
from genai.retrieval.hybrid_search import reciprocal_rank_fusion
from genai.retrieval.reranker import CrossEncoderReranker

from genai.evaluation.evaluate_retrieval import (
    load_dataset,
    calculate_metrics,
)


# ==========================================================
# CONFIGURATION
# ==========================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

OUTPUT_FILE = (
    PROJECT_ROOT
    / "genai"
    / "evaluation"
    / "targeted_multi_query_rrf100_results.json"
)

TARGET_QUERY_IDS = ["Q005", "Q006"]

RETRIEVAL_TOP_K = 20
RRF_TOP_K = 60
FINAL_TOP_K = 20
RRF_K = 60


# ==========================================================
# QUERY EXPANSION
# ==========================================================
QUERY_VARIANTS = {
    "Q005": [
        # Original question
        "How should workplace incidents and near misses be reported?",

        # Existing general expansions
        "What is the incident reporting procedure?",
        "How should workplace injuries and hazards be recorded?",
        "What is the process for reporting unsafe conditions?",
        "How are incidents investigated and corrective actions assigned?",

        # New targeted expansions
        "Who is responsible for reporting, investigating, and reviewing workplace incidents?",
        "What are the duties of workers, supervisors, EHS investigators, and site managers after an incident?",
        "How should corrective actions be assigned, monitored, and verified to prevent recurrence?",
    ],

    "Q006": [
        # Original question
        "What precautions should workers follow when handling chemicals?",

        # Existing general expansions
        "Chemical storage and handling safety procedures",
        "How should hazardous substances be transferred and stored?",
        "What PPE is required when handling chemical substances?",
        "How should incompatible chemicals be segregated?",

        # New targeted expansions
        "What checks must workers complete before handling a chemical product or container?",
        "How should workers verify chemical identity, authorisation, container condition, and approved storage location?",
        "What should workers do after using chemicals, including closing containers and reporting leaks or exposure?",
    ],
}


# ==========================================================
# HELPER FUNCTIONS
# ==========================================================

def deduplicate_results(results):

    unique_results = []
    seen = set()

    for result in results:

        chunk_id = result["chunk_id"]

        if chunk_id not in seen:
            seen.add(chunk_id)
            unique_results.append(result)

    return unique_results


def candidate_coverage(results, relevant_chunks):

    relevant_ids = {
        chunk_id
        for chunk_id, grade in relevant_chunks.items()
        if grade > 0
    }

    retrieved_ids = {
        result["chunk_id"]
        for result in results
    }

    found = retrieved_ids & relevant_ids

    return {
        "found": len(found),
        "total": len(relevant_ids),
        "recall": round(
            len(found) / len(relevant_ids), 4
        ) if relevant_ids else 0.0,
        "missing_chunks": sorted(relevant_ids - retrieved_ids),
    }


def print_metrics(title, metrics):

    print(f"\n{title}")
    print("-" * 55)

    for metric, value in metrics.items():
        print(f"{metric:<15}: {value:.4f}")


def retrieve_single_query(query, bm25_engine):

    dense_results = semantic_search(
        query=query,
        top_k=RETRIEVAL_TOP_K,
    )

    bm25_results = bm25_engine.search(
        query=query,
        top_k=RETRIEVAL_TOP_K,
    )

    return dense_results, bm25_results


# ==========================================================
# BASELINE: ORIGINAL SINGLE-QUERY RETRIEVAL
# ==========================================================

def evaluate_baseline(
    query,
    relevant_chunks,
    bm25_engine,
    reranker,
):

    print("\nRunning original single-query baseline...")

    dense_results, bm25_results = retrieve_single_query(
        query,
        bm25_engine,
    )

    fused_results = reciprocal_rank_fusion(
        ranked_lists=[
            ("dense", dense_results),
            ("bm25", bm25_results),
        ],
        top_k=RETRIEVAL_TOP_K,
        rrf_k=RRF_K,
    )

    reranked_results = reranker.rerank(
        query=query,
        documents=fused_results,
        top_k=FINAL_TOP_K,
    )

    return {
        "dense": calculate_metrics(
            dense_results,
            relevant_chunks,
        ),
        "bm25": calculate_metrics(
            bm25_results,
            relevant_chunks,
        ),
        "hybrid_rrf": calculate_metrics(
            fused_results,
            relevant_chunks,
        ),
        "hybrid_reranked": calculate_metrics(
            reranked_results,
            relevant_chunks,
        ),
        "candidate_coverage": candidate_coverage(
            deduplicate_results(
                dense_results + bm25_results
            ),
            relevant_chunks,
        ),
        "reranked_chunk_ids": [
            result["chunk_id"]
            for result in reranked_results
        ],
    }


# ==========================================================
# MULTI-QUERY RETRIEVAL
# ==========================================================

def evaluate_multi_query(
    query_id,
    original_query,
    relevant_chunks,
    bm25_engine,
    reranker,
):

    variants = QUERY_VARIANTS[query_id]

    print("\n" + "=" * 70)
    print(f"MULTI-QUERY EXPERIMENT: {query_id}")
    print("Original question:", original_query)
    print("=" * 70)

    ranked_lists = []
    all_candidates = []

    # ------------------------------------------------------
    # Retrieve dense + BM25 results for every query variant
    # ------------------------------------------------------

    for index, variant in enumerate(variants, start=1):

        print(f"\nVariant {index}/{len(variants)}:")
        print(variant)

        dense_results, bm25_results = retrieve_single_query(
            variant,
            bm25_engine,
        )

        ranked_lists.append(
            (f"variant_{index}_dense", dense_results)
        )

        ranked_lists.append(
            (f"variant_{index}_bm25", bm25_results)
        )

        all_candidates.extend(dense_results)
        all_candidates.extend(bm25_results)

    # ------------------------------------------------------
    # Candidate union
    # ------------------------------------------------------

    candidate_union = deduplicate_results(all_candidates)

    coverage = candidate_coverage(
        candidate_union,
        relevant_chunks,
    )

    print("\n========== CANDIDATE UNION ==========")

    print(
        f"Unique candidates: {len(candidate_union)}"
    )

    print(
        f"Relevant chunks found: "
        f"{coverage['found']}/{coverage['total']}"
    )

    print(
        f"Candidate recall: {coverage['recall']:.4f}"
    )

    if coverage["missing_chunks"]:
        print("\nStill missing relevant chunks:")

        for chunk_id in coverage["missing_chunks"]:
            print("-", chunk_id)

    # ------------------------------------------------------
    # Reciprocal Rank Fusion
    # ------------------------------------------------------

    print("\nRunning multi-source RRF...")

    fused_results = reciprocal_rank_fusion(
        ranked_lists=ranked_lists,
        top_k=RRF_TOP_K,
        rrf_k=RRF_K,
    )

    print(
        f"RRF candidates generated: {len(fused_results)}"
    )

    # ------------------------------------------------------
    # Reranking
    # ------------------------------------------------------

    print("\nRunning cross-encoder reranking...")

    reranked_results = reranker.rerank(
        query=original_query,
        documents=fused_results,
        top_k=FINAL_TOP_K,
    )

    # ------------------------------------------------------
    # Evaluation
    # ------------------------------------------------------

    rrf_metrics = calculate_metrics(
        fused_results,
        relevant_chunks,
    )

    reranked_metrics = calculate_metrics(
        reranked_results,
        relevant_chunks,
    )

    print_metrics("MULTI-QUERY RRF", rrf_metrics)

    print_metrics(
        "MULTI-QUERY + RERANKER",
        reranked_metrics,
    )

    print("\nTop reranked chunks:")

    for rank, result in enumerate(
        reranked_results[:10],
        start=1,
    ):
        print(f"{rank:>2}. {result['chunk_id']}")

    return {
        "query_variants": variants,
        "candidate_count": len(candidate_union),
        "candidate_coverage": coverage,
        "rrf_candidate_count": len(fused_results),
        "multi_query_rrf": rrf_metrics,
        "multi_query_reranked": reranked_metrics,
        "rrf_chunk_ids": [
            result["chunk_id"]
            for result in fused_results
        ],
        "reranked_chunk_ids": [
            result["chunk_id"]
            for result in reranked_results
        ],
    }


# ==========================================================
# MAIN
# ==========================================================

def main():

    print("\n" + "=" * 70)
    print(" SITESENSE MULTI-QUERY RETRIEVAL EXPERIMENT")
    print("=" * 70)

    dataset = load_dataset()

    target_queries = {
        item["query_id"]: item
        for item in dataset["queries"]
        if item["query_id"] in TARGET_QUERY_IDS
    }

    missing_ids = set(TARGET_QUERY_IDS) - set(target_queries)

    if missing_ids:
        raise ValueError(
            f"Missing evaluation queries: {sorted(missing_ids)}"
        )

    print("\nInitializing BM25...")

    bm25_engine = BM25Search()

    print("\nInitializing cross-encoder...")

    reranker = CrossEncoderReranker()

    all_results = {
        "experiment": "targeted_multi_query_retrieval",
        "target_query_ids": TARGET_QUERY_IDS,
        "retrieval_top_k": RETRIEVAL_TOP_K,
        "rrf_top_k": RRF_TOP_K,
        "final_top_k": FINAL_TOP_K,
        "queries": {},
    }

    for query_id in TARGET_QUERY_IDS:

        item = target_queries[query_id]

        original_query = item["query"]
        relevant_chunks = item["relevant_chunks"]

        print("\n" + "#" * 70)
        print(f"BASELINE EVALUATION: {query_id}")
        print("#" * 70)

        baseline = evaluate_baseline(
            original_query,
            relevant_chunks,
            bm25_engine,
            reranker,
        )

        print_metrics(
            "BASELINE HYBRID + RERANKER",
            baseline["hybrid_reranked"],
        )

        multi_query = evaluate_multi_query(
            query_id,
            original_query,
            relevant_chunks,
            bm25_engine,
            reranker,
        )

        all_results["queries"][query_id] = {
            "original_query": original_query,
            "baseline": baseline,
            "multi_query": multi_query,
        }

        print("\n========== COMPARISON ==========")

        print(
            "Baseline reranked Recall@5:",
            baseline["hybrid_reranked"]["Recall@5"],
        )

        print(
            "Multi-query reranked Recall@5:",
            multi_query["multi_query_reranked"]["Recall@5"],
        )

        print(
            "Baseline reranked nDCG@5:",
            baseline["hybrid_reranked"]["nDCG@5"],
        )

        print(
            "Multi-query reranked nDCG@5:",
            multi_query["multi_query_reranked"]["nDCG@5"],
        )

    # ------------------------------------------------------
    # SAVE RESULTS
    # ------------------------------------------------------

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            all_results,
            file,
            indent=4,
            ensure_ascii=False,
        )

    print("\n" + "=" * 70)
    print("MULTI-QUERY EXPERIMENT COMPLETED")
    print("=" * 70)

    print("\nResults saved to:")
    print(OUTPUT_FILE)


if __name__ == "__main__":
    main()
