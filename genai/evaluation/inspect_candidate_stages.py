
import json
from pathlib import Path

from genai.retrieval.bm25_search import BM25Search
from genai.retrieval.pgvector_search import semantic_search
from genai.retrieval.hybrid_search import reciprocal_rank_fusion
from genai.retrieval.reranker import CrossEncoderReranker


# ==========================================================
# CONFIGURATION
# ==========================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATASET_FILE = PROJECT_ROOT / "genai" / "evaluation" / "retrieval_dataset.json"

OUTPUT_FILE = (
    PROJECT_ROOT
    / "genai"
    / "evaluation"
    / "candidate_stage_diagnostics.json"
)

BASELINE_CANDIDATES = 20
EXPANDED_CANDIDATES = 40
RRF_K = 60


# ==========================================================
# HELPERS
# ==========================================================

def load_dataset():
    with open(DATASET_FILE, "r", encoding="utf-8") as file:
        dataset = json.load(file)

    if len(dataset["queries"]) != 8:
        raise ValueError("Expected the existing 8-query benchmark.")

    return dataset


def rank_map(results):
    return {
        result["chunk_id"]: rank
        for rank, result in enumerate(results, start=1)
    }


def calculate_recall(results, relevant_chunks):
    relevant_ids = {
        chunk_id
        for chunk_id, grade in relevant_chunks.items()
        if grade > 0
    }

    retrieved_ids = {
        result["chunk_id"]
        for result in results
    }

    found = relevant_ids & retrieved_ids

    return {
        "found": len(found),
        "total": len(relevant_ids),
        "recall": round(len(found) / len(relevant_ids), 4)
        if relevant_ids else 0.0,
        "found_chunks": sorted(found),
        "missing_chunks": sorted(relevant_ids - found),
    }


def build_rrf(dense, bm25, candidate_count):
    return reciprocal_rank_fusion(
        ranked_lists=[
            ("dense", dense[:candidate_count]),
            ("bm25", bm25[:candidate_count]),
        ],
        top_k=candidate_count,
        rrf_k=RRF_K,
    )


def stage_ranks(results, relevant_chunks):
    ranks = rank_map(results)

    return {
        chunk_id: {
            "grade": grade,
            "rank": ranks.get(chunk_id),
        }
        for chunk_id, grade in relevant_chunks.items()
        if grade > 0
    }


def print_stage(name, results, relevant_chunks):
    recall = calculate_recall(results, relevant_chunks)

    print(
        f"{name:<22} "
        f"{recall['found']}/{recall['total']} "
        f"Recall: {recall['recall']:.4f}"
    )

    return recall


# ==========================================================
# MAIN DIAGNOSTIC
# ==========================================================

def main():

    dataset = load_dataset()

    print("=" * 85)
    print("SITESENSE CANDIDATE-STAGE DIAGNOSTICS")
    print("=" * 85)

    print("\nLoading BM25...")
    bm25_engine = BM25Search()

    print("\nLoading cross-encoder reranker...")
    reranker = CrossEncoderReranker()

    all_diagnostics = []

    for query_number, item in enumerate(dataset["queries"], start=1):

        query_id = item["query_id"]
        query = item["query"]
        relevant_chunks = item["relevant_chunks"]

        print("\n" + "=" * 85)
        print(f"{query_id}: {query}")
        print("=" * 85)

        # --------------------------------------------------
        # 1. DENSE RETRIEVAL - TOP 40
        # --------------------------------------------------

        print("\nRunning dense retrieval...")

        dense_results = semantic_search(
            query=query,
            top_k=EXPANDED_CANDIDATES,
        )

        # --------------------------------------------------
        # 2. BM25 RETRIEVAL - TOP 40
        # --------------------------------------------------

        print("Running BM25 retrieval...")

        bm25_results = bm25_engine.search(
            query=query,
            top_k=EXPANDED_CANDIDATES,
        )

        # --------------------------------------------------
        # 3. CANDIDATE UNION
        # --------------------------------------------------

        candidate_union = {
            result["chunk_id"]: result
            for result in dense_results + bm25_results
        }

        union_results = list(candidate_union.values())

        # --------------------------------------------------
        # 4. RRF TOP 20 AND TOP 40
        # --------------------------------------------------

        print("Running RRF Top 20...")

        rrf20 = build_rrf(
            dense_results,
            bm25_results,
            BASELINE_CANDIDATES,
        )

        print("Running RRF Top 40...")

        rrf40 = build_rrf(
            dense_results,
            bm25_results,
            EXPANDED_CANDIDATES,
        )

        # --------------------------------------------------
        # 5. RERANK BOTH CANDIDATE SETS
        # --------------------------------------------------

        print("Reranking RRF Top 20...")

        reranked20 = reranker.rerank(
            query=query,
            documents=rrf20,
            top_k=BASELINE_CANDIDATES,
        )

        print("Reranking RRF Top 40...")

        reranked40 = reranker.rerank(
            query=query,
            documents=rrf40,
            top_k=EXPANDED_CANDIDATES,
        )

        # --------------------------------------------------
        # 6. STAGE RECALL
        # --------------------------------------------------

        print("\nSTAGE RECALL")
        print("-" * 65)

        stages = {
            "Dense Top 20": dense_results[:20],
            "BM25 Top 20": bm25_results[:20],
            "Candidate Union": union_results,
            "RRF Top 20": rrf20,
            "RRF Top 40": rrf40,
            "Reranked Top 20": reranked20,
            "Reranked Top 40": reranked40,
        }

        stage_metrics = {}

        for stage_name, results in stages.items():
            stage_metrics[stage_name] = print_stage(
                stage_name,
                results,
                relevant_chunks,
            )

        # --------------------------------------------------
        # 7. RELEVANT CHUNK RANK COMPARISON
        # --------------------------------------------------

        print("\nRELEVANT CHUNK RANK COMPARISON")
        print("-" * 85)

        rank_maps = {
            name: rank_map(results)
            for name, results in stages.items()
        }

        print(
            f"{'CHUNK ID':<24}"
            f"{'GRADE':<8}"
            f"{'DENSE':<9}"
            f"{'BM25':<9}"
            f"{'UNION':<9}"
            f"{'RRF20':<9}"
            f"{'RRF40':<9}"
            f"{'RR20':<9}"
            f"{'RR40':<9}"
        )

        for chunk_id, grade in relevant_chunks.items():

            if grade <= 0:
                continue

            values = [
                rank_maps["Dense Top 20"].get(chunk_id, "-"),
                rank_maps["BM25 Top 20"].get(chunk_id, "-"),
                rank_maps["Candidate Union"].get(chunk_id, "-"),
                rank_maps["RRF Top 20"].get(chunk_id, "-"),
                rank_maps["RRF Top 40"].get(chunk_id, "-"),
                rank_maps["Reranked Top 20"].get(chunk_id, "-"),
                rank_maps["Reranked Top 40"].get(chunk_id, "-"),
            ]

            print(
                f"{chunk_id:<24}"
                f"{grade:<8}"
                + "".join(f"{str(value):<9}" for value in values)
            )

        # --------------------------------------------------
        # 8. SAVE QUERY DIAGNOSTICS
        # --------------------------------------------------

        all_diagnostics.append({
            "query_id": query_id,
            "query": query,
            "relevant_chunks": relevant_chunks,
            "stage_metrics": stage_metrics,
            "relevant_chunk_ranks": stage_ranks(
                stages["Candidate Union"],
                relevant_chunks,
            ),
            "rankings": {
                name: [
                    {
                        "chunk_id": result["chunk_id"],
                        "rerank_score": result.get("rerank_score"),
                        "rrf_score": result.get("rrf_score"),
                    }
                    for result in results
                ]
                for name, results in stages.items()
            },
        })

    # ------------------------------------------------------
    # 9. SAVE FINAL REPORT
    # ------------------------------------------------------

    output = {
        "dataset_name": dataset.get("dataset_name"),
        "dataset_version": dataset.get("version"),
        "total_queries": len(all_diagnostics),
        "baseline_candidates": BASELINE_CANDIDATES,
        "expanded_candidates": EXPANDED_CANDIDATES,
        "rrf_k": RRF_K,
        "results": all_diagnostics,
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as file:
        json.dump(
            output,
            file,
            indent=4,
            ensure_ascii=False,
        )

    print("\n" + "=" * 85)
    print("CANDIDATE-STAGE DIAGNOSTICS COMPLETED")
    print("=" * 85)
    print("\nReport saved to:")
    print(OUTPUT_FILE)


if __name__ == "__main__":
    main()
