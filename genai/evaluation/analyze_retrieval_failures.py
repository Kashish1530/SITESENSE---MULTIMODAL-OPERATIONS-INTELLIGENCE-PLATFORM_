
import json
from pathlib import Path

from genai.retrieval.pgvector_search import semantic_search
from genai.retrieval.bm25_search import BM25Search
from genai.retrieval.hybrid_search import reciprocal_rank_fusion
from genai.retrieval.reranker import CrossEncoderReranker


# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

ROOT = Path(__file__).resolve().parents[2]

DATASET_FILE = ROOT / "genai/evaluation/retrieval_dataset.json"

CANDIDATE_COUNT = 20
FINAL_COUNT = 20

TARGET_QUERY_IDS = {"Q003", "Q005", "Q006", "Q007"}


# --------------------------------------------------
# HELPERS
# --------------------------------------------------

def get_chunk_id(result):
    return result.get("chunk_id")


def get_rank_map(results):
    return {
        get_chunk_id(result): rank
        for rank, result in enumerate(results, start=1)
        if get_chunk_id(result)
    }


def display_rank(rank):
    return str(rank) if rank is not None else "NOT FOUND"


# --------------------------------------------------
# LOAD DATASET
# --------------------------------------------------

with open(DATASET_FILE, encoding="utf-8") as file:
    dataset = json.load(file)

queries = [
    query
    for query in dataset["queries"]
    if query["query_id"] in TARGET_QUERY_IDS
]

if len(queries) != len(TARGET_QUERY_IDS):
    raise ValueError(
        "One or more target queries are missing from the dataset."
    )


# --------------------------------------------------
# INITIALIZE RETRIEVAL COMPONENTS
# --------------------------------------------------

print("\nINITIALIZING RETRIEVAL FAILURE ANALYZER")
print("=" * 65)

print("\nInitializing BM25...")
bm25 = BM25Search()

print("\nInitializing cross-encoder...")
reranker = CrossEncoderReranker()

print("\nAll components initialized.")


# --------------------------------------------------
# ANALYZE EACH QUERY
# --------------------------------------------------

for query_data in queries:

    query_id = query_data["query_id"]
    question = query_data["query"]
    relevant_chunks = query_data["relevant_chunks"]

    print("\n")
    print("=" * 85)
    print(f"{query_id}: {question}")
    print("=" * 85)

    # Stage 1: Semantic retrieval
    print("\nRunning semantic search...")

    semantic_results = semantic_search(
        question,
        top_k=CANDIDATE_COUNT
    )

    # Stage 2: BM25 retrieval
    print("Running BM25 search...")

    bm25_results = bm25.search(
        question,
        top_k=CANDIDATE_COUNT
    )

    # Stage 3: Hybrid fusion
    print("Running Reciprocal Rank Fusion...")

    # Full fusion pool: maximum 40 unique candidates
    full_hybrid_results = reciprocal_rank_fusion(
        [
            ("dense", semantic_results),
            ("bm25", bm25_results)
        ],
        top_k=CANDIDATE_COUNT * 2,
        rrf_k=60
    )

    # Actual production candidate pool: top 20
    hybrid_results = full_hybrid_results[:CANDIDATE_COUNT]

    # Stage 4: Cross-encoder reranking
    print("Running cross-encoder reranking...")

    reranked_results = reranker.rerank(
        question,
        hybrid_results,
        top_k=FINAL_COUNT
    )

    # Build rank lookups
    semantic_ranks = get_rank_map(semantic_results)
    bm25_ranks = get_rank_map(bm25_results)

    # Actual RRF top-20 ranks
    hybrid_ranks = get_rank_map(hybrid_results)

    # Full RRF pool ranks for diagnosis
    full_hybrid_ranks = get_rank_map(full_hybrid_results)

    reranked_ranks = get_rank_map(reranked_results)

    # --------------------------------------------------
    # RELEVANT CHUNK ANALYSIS
    # --------------------------------------------------

    print("\nRELEVANT CHUNK RETRIEVAL ANALYSIS")
    print("-" * 85)

    print(
        f"{'CHUNK ID':<25}"
        f"{'GRADE':<8}"
        f"{'SEM':<8}"
        f"{'BM25':<8}"
        f"{'RRF20':<8}"
        f"{'RRF40':<8}"
        f"{'RERANK':<8}"
    )

    print("-" * 85)

    for chunk_id, relevance in relevant_chunks.items():

        sem_rank = semantic_ranks.get(chunk_id)
        bm25_rank = bm25_ranks.get(chunk_id)
        rrf_rank = hybrid_ranks.get(chunk_id)
        rerank_rank = reranked_ranks.get(chunk_id)

        print(
            f"{chunk_id:<25}"
            f"{relevance:<8}"
            f"{display_rank(sem_rank):<8}"
            f"{display_rank(bm25_rank):<8}"
            f"{display_rank(rrf_rank):<8}"
            f"{display_rank(full_hybrid_ranks.get(chunk_id)):<8}"
            f"{display_rank(rerank_rank):<8}"
        )

    # --------------------------------------------------
    # STAGE RECALL
    # --------------------------------------------------

    total_relevant = len(relevant_chunks)

    stages = {
        "Semantic": semantic_ranks,
        "BM25": bm25_ranks,
        "Hybrid RRF": hybrid_ranks,
        "Hybrid Reranked": reranked_ranks
    }

    print("\nSTAGE RECALL")
    print("-" * 65)

    for stage_name, rank_map in stages.items():

        found = sum(
            1
            for chunk_id in relevant_chunks
            if chunk_id in rank_map
        )

        recall = found / total_relevant if total_relevant else 0

        print(
            f"{stage_name:<22}"
            f"{found}/{total_relevant:<8}"
            f"Recall: {recall:.4f}"
        )

    # --------------------------------------------------
    # TOP 10 FINAL RESULTS
    # --------------------------------------------------

    print("\nTOP 10 AFTER RERANKING")
    print("-" * 65)

    for rank, result in enumerate(reranked_results[:10], start=1):

        chunk_id = get_chunk_id(result)

        relevance = relevant_chunks.get(chunk_id, 0)

        score = result.get("rerank_score", "N/A")

        print(
            f"{rank:>2}. {chunk_id:<25}"
            f"Relevance: {relevance} | "
            f"Score: {score}"
        )

    # --------------------------------------------------
    # DIAGNOSIS
    # --------------------------------------------------

    print("\nAUTOMATED DIAGNOSIS")
    print("-" * 65)
    
    for chunk_id in relevant_chunks:
    
        sem = semantic_ranks.get(chunk_id)
        bm = bm25_ranks.get(chunk_id)
        rrf20 = hybrid_ranks.get(chunk_id)
        rrf40 = full_hybrid_ranks.get(chunk_id)
        rerank = reranked_ranks.get(chunk_id)
    
        if sem is None and bm is None:
            diagnosis = "CANDIDATE RETRIEVAL FAILURE"
    
        elif rrf40 is None:
            diagnosis = "UNEXPECTED FUSION FAILURE"
    
        elif rrf20 is None:
            diagnosis = "RRF TOP-20 CUTOFF"
    
        elif rerank is None:
            diagnosis = "RERANKING / FINAL CUTOFF FAILURE"
    
        elif rerank > rrf20:
            diagnosis = "DEMOTED BY RERANKER"
    
        else:
            diagnosis = "RETAINED OR IMPROVED"
    
        print(f"{chunk_id}: {diagnosis}")


print("\n")
print("=" * 85)
print("RETRIEVAL FAILURE ANALYSIS COMPLETED")
print("=" * 85)
