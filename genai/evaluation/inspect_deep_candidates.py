
import json
from pathlib import Path

from genai.retrieval.pgvector_search import semantic_search
from genai.retrieval.bm25_search import BM25Search
from genai.retrieval.hybrid_search import reciprocal_rank_fusion


ROOT = Path(__file__).resolve().parents[2]

DATASET_FILE = ROOT / "genai/evaluation/retrieval_dataset.json"

TARGET_QUERY_IDS = {"Q003", "Q005", "Q006", "Q007"}

DEEP_K = 50


def get_rank_map(results):
    return {
        result["chunk_id"]: rank
        for rank, result in enumerate(results, start=1)
    }


def show_rank(rank):
    return str(rank) if rank is not None else "NOT FOUND"


# Load evaluation dataset
with open(DATASET_FILE, encoding="utf-8") as file:
    dataset = json.load(file)


queries = [
    q for q in dataset["queries"]
    if q["query_id"] in TARGET_QUERY_IDS
]

if len(queries) != len(TARGET_QUERY_IDS):
    raise ValueError("Missing one or more target queries.")


# Initialize BM25 once
print("\nInitializing BM25...")
bm25 = BM25Search()

print("\nDEEP CANDIDATE RETRIEVAL ANALYSIS")
print("=" * 100)


for query_data in queries:

    query_id = query_data["query_id"]
    question = query_data["query"]
    relevant_chunks = query_data["relevant_chunks"]

    print("\n" + "=" * 100)
    print(f"{query_id}: {question}")
    print("=" * 100)

    # Semantic top 50
    print("\nRunning semantic top 50...")
    semantic_results = semantic_search(
        question,
        top_k=DEEP_K
    )

    # BM25 top 50
    print("Running BM25 top 50...")
    bm25_results = bm25.search(
        question,
        top_k=DEEP_K
    )

    # RRF over the complete retrieved lists
    print("Running RRF over top 50 + top 50...")
    full_rrf_results = reciprocal_rank_fusion(
        [
            ("dense", semantic_results),
            ("bm25", bm25_results)
        ],
        top_k=DEEP_K * 2,
        rrf_k=60
    )

    semantic_ranks = get_rank_map(semantic_results)
    bm25_ranks = get_rank_map(bm25_results)
    rrf_ranks = get_rank_map(full_rrf_results)

    print("\nRELEVANT CHUNK DEEP RANKS")
    print("-" * 100)

    print(
        f"{'CHUNK ID':<25}"
        f"{'GRADE':<8}"
        f"{'SEM50':<12}"
        f"{'BM2550':<12}"
        f"{'RRF100':<12}"
        f"{'STATUS'}"
    )

    print("-" * 100)

    for chunk_id, grade in relevant_chunks.items():

        sem_rank = semantic_ranks.get(chunk_id)
        bm_rank = bm25_ranks.get(chunk_id)
        rrf_rank = rrf_ranks.get(chunk_id)

        if sem_rank is None and bm_rank is None:
            status = "NOT FOUND IN EITHER TOP 50"

        elif rrf_rank is not None and rrf_rank <= 20:
            status = "IN PRODUCTION RRF TOP 20"

        elif rrf_rank is not None:
            status = "FOUND ONLY AFTER DEEPER SEARCH"

        else:
            status = "UNEXPECTED: CHECK FUSION"

        print(
            f"{chunk_id:<25}"
            f"{grade:<8}"
            f"{show_rank(sem_rank):<12}"
            f"{show_rank(bm_rank):<12}"
            f"{show_rank(rrf_rank):<12}"
            f"{status}"
        )

    print("\nDEEP STAGE RECALL")
    print("-" * 65)

    total = len(relevant_chunks)

    stages = {
        "Semantic Top 50": semantic_ranks,
        "BM25 Top 50": bm25_ranks,
        "RRF Top 20": {
            chunk_id: rank
            for chunk_id, rank in rrf_ranks.items()
            if rank <= 20
        },
        "RRF Top 100": rrf_ranks
    }

    for name, ranks in stages.items():

        found = sum(
            1 for chunk_id in relevant_chunks
            if chunk_id in ranks
        )

        print(
            f"{name:<22}"
            f"{found}/{total:<8}"
            f"Recall: {found / total:.4f}"
        )


print("\n" + "=" * 100)
print("DEEP CANDIDATE INSPECTION COMPLETED")
print("=" * 100)
