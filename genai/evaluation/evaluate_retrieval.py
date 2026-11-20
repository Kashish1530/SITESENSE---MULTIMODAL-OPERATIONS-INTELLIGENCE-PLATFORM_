
import json
import math
from pathlib import Path

from genai.retrieval.pgvector_search import semantic_search
from genai.retrieval.bm25_search import BM25Search
from genai.retrieval.hybrid_search import reciprocal_rank_fusion
from genai.retrieval.reranker import CrossEncoderReranker


# ==========================================================
# CONFIGURATION
# ==========================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATASET_FILE = (
    PROJECT_ROOT
    / "genai"
    / "evaluation"
    / "retrieval_dataset.json"
)

OUTPUT_FILE = (
    PROJECT_ROOT
    / "genai"
    / "evaluation"
    / "retrieval_evaluation_results.json"
)

TOP_K = 20

RRF_K = 60


# ==========================================================
# LOAD EVALUATION DATASET
# ==========================================================

def load_dataset():

    with open(DATASET_FILE, "r", encoding="utf-8") as file:
        dataset = json.load(file)

    if not dataset.get("queries"):
        raise ValueError("Evaluation dataset contains no queries.")

    for item in dataset["queries"]:

        if not item.get("query"):
            raise ValueError("An evaluation query is empty.")

        if not item.get("relevant_chunks"):
            raise ValueError(
                f"No relevant chunks defined for {item.get('query_id')}"
            )

        for chunk_id, grade in item["relevant_chunks"].items():

            if not isinstance(grade, int) or not 0 <= grade <= 3:
                raise ValueError(
                    f"Invalid relevance grade: {chunk_id} = {grade}"
                )

    return dataset


# ==========================================================
# REMOVE DUPLICATE RESULTS
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


# ==========================================================
# RETRIEVAL METRICS
# ==========================================================

def recall_at_k(results, relevant_chunks, k):

    relevant_ids = {
        chunk_id
        for chunk_id, grade in relevant_chunks.items()
        if grade > 0
    }

    if not relevant_ids:
        return 0.0

    retrieved_ids = {
        result["chunk_id"]
        for result in results[:k]
    }

    return len(retrieved_ids & relevant_ids) / len(relevant_ids)


def reciprocal_rank(results, relevant_chunks):

    relevant_ids = {
        chunk_id
        for chunk_id, grade in relevant_chunks.items()
        if grade > 0
    }

    for rank, result in enumerate(results, start=1):

        if result["chunk_id"] in relevant_ids:
            return 1.0 / rank

    return 0.0


def dcg_at_k(results, relevant_chunks, k):

    dcg = 0.0

    for rank, result in enumerate(results[:k], start=1):

        grade = relevant_chunks.get(result["chunk_id"], 0)

        gain = (2 ** grade) - 1

        discount = math.log2(rank + 1)

        dcg += gain / discount

    return dcg


def ndcg_at_k(results, relevant_chunks, k):

    actual_dcg = dcg_at_k(
        results,
        relevant_chunks,
        k
    )

    ideal_grades = sorted(
        relevant_chunks.values(),
        reverse=True
    )

    ideal_results = [
        {"chunk_id": f"ideal_{index}"}
        for index in range(len(ideal_grades))
    ]

    ideal_relevance = {
        f"ideal_{index}": grade
        for index, grade in enumerate(ideal_grades)
    }

    ideal_dcg = dcg_at_k(
        ideal_results,
        ideal_relevance,
        k
    )

    if ideal_dcg == 0:
        return 0.0

    return actual_dcg / ideal_dcg


# ==========================================================
# EVALUATE ONE RANKED RESULT LIST
# ==========================================================

def calculate_metrics(results, relevant_chunks):

    results = deduplicate_results(results)

    return {
        "Recall@5": round(
            recall_at_k(results, relevant_chunks, 5), 4
        ),
        "Recall@10": round(
            recall_at_k(results, relevant_chunks, 10), 4
        ),
        "MRR": round(
            reciprocal_rank(results, relevant_chunks), 4
        ),
        "nDCG@5": round(
            ndcg_at_k(results, relevant_chunks, 5), 4
        ),
        "nDCG@10": round(
            ndcg_at_k(results, relevant_chunks, 10), 4
        )
    }


# ==========================================================
# PRINT RESULTS
# ==========================================================

def print_metrics(name, metrics):

    print(f"\n{name}")

    print("-" * 55)

    for metric, value in metrics.items():

        print(f"{metric:<15}: {value:.4f}")


def print_ranked_chunks(name, results):

    print(f"\n{name} — TOP 10 CHUNKS")

    print("-" * 55)

    for rank, result in enumerate(results[:10], start=1):

        print(
            f"{rank:>2}. {result['chunk_id']}"
        )


# ==========================================================
# MAIN EVALUATION
# ==========================================================

def main():

    print("\n==========================================")
    print(" SITESENSE RETRIEVAL EVALUATION")
    print("==========================================")

    dataset = load_dataset()

    print("\nDataset:", dataset["dataset_name"])
    print("Total queries:", len(dataset["queries"]))

    # Initialize reusable retrieval components.
    print("\nInitializing BM25...")
    bm25_engine = BM25Search()

    print("\nInitializing reranker...")
    reranker = CrossEncoderReranker()

    all_results = []

    # Evaluate every labelled query.
    for query_number, item in enumerate(
        dataset["queries"], start=1
    ):

        query_id = item["query_id"]
        query = item["query"]
        relevant_chunks = item["relevant_chunks"]

        print("\n" + "=" * 65)
        print(f"QUERY {query_number}: {query_id}")
        print("Question:", query)
        print("=" * 65)

        # --------------------------------------------------
        # 1. SEMANTIC RETRIEVAL
        # --------------------------------------------------

        print("\nRunning semantic search...")

        dense_results = semantic_search(
            query=query,
            top_k=TOP_K
        )

        # --------------------------------------------------
        # 2. BM25 RETRIEVAL
        # --------------------------------------------------

        print("Running BM25 search...")

        bm25_results = bm25_engine.search(
            query=query,
            top_k=TOP_K
        )

        # --------------------------------------------------
        # 3. HYBRID RETRIEVAL USING RRF
        # --------------------------------------------------

        print("Running Reciprocal Rank Fusion...")

        hybrid_results = reciprocal_rank_fusion(
            ranked_lists=[
                ("dense", dense_results),
                ("bm25", bm25_results)
            ],
            top_k=TOP_K,
            rrf_k=RRF_K
        )

        # --------------------------------------------------
        # 4. CROSS-ENCODER RERANKING
        # --------------------------------------------------

        print("Running cross-encoder reranking...")

        reranked_results = reranker.rerank(
            query=query,
            documents=hybrid_results,
            top_k=TOP_K
        )

        # --------------------------------------------------
        # CALCULATE METRICS
        # --------------------------------------------------

        rankings = {
            "Semantic": dense_results,
            "BM25": bm25_results,
            "Hybrid_RRF": hybrid_results,
            "Hybrid_Reranked": reranked_results
        }

        query_result = {
            "query_id": query_id,
            "query": query,
            "relevant_chunks": relevant_chunks,
            "methods": {}
        }

        for method_name, results in rankings.items():

            metrics = calculate_metrics(
                results,
                relevant_chunks
            )

            query_result["methods"][method_name] = {
                "metrics": metrics,
                "ranked_chunk_ids": [
                    result["chunk_id"]
                    for result in deduplicate_results(results)
                ]
            }

            print_metrics(method_name, metrics)

        # Show ranked chunks for inspection.
        for method_name, results in rankings.items():

            print_ranked_chunks(
                method_name,
                results
            )

        all_results.append(query_result)

    # ------------------------------------------------------
    # SAVE RESULTS
    # ------------------------------------------------------

    output = {
        "dataset_name": dataset["dataset_name"],
        "dataset_version": dataset.get("version", "unknown"),
        "total_queries": len(all_results),
        "top_k": TOP_K,
        "results": all_results
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as file:

        json.dump(
            output,
            file,
            indent=4,
            ensure_ascii=False
        )

    print("\n" + "=" * 65)
    print("EVALUATION COMPLETED")
    print("=" * 65)

    print("\nResults saved to:")
    print(OUTPUT_FILE)


if __name__ == "__main__":
    main()
