
from collections import defaultdict

from genai.retrieval.bm25_search import BM25Search
from genai.retrieval.pgvector_search import semantic_search
from genai.retrieval.reranker import CrossEncoderReranker


# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

RRF_K = 60
CANDIDATE_COUNT = 20
DEFAULT_TOP_K = 5


# --------------------------------------------------
# RECIPROCAL RANK FUSION
# --------------------------------------------------

def reciprocal_rank_fusion(
    ranked_lists,
    top_k=DEFAULT_TOP_K,
    rrf_k=RRF_K,
):

    scores = defaultdict(float)
    documents = {}
    component_ranks = defaultdict(dict)

    for source_name, ranked_list in ranked_lists:

        for rank, result in enumerate(ranked_list, start=1):

            chunk_id = result["chunk_id"]

            scores[chunk_id] += 1.0 / (rrf_k + rank)

            component_ranks[chunk_id][source_name] = rank

            if chunk_id not in documents:
                documents[chunk_id] = result.copy()

    ranked_chunks = sorted(
        scores.items(),
        key=lambda item: item[1],
        reverse=True,
    )

    fused_results = []

    for chunk_id, score in ranked_chunks[:top_k]:

        result = documents[chunk_id].copy()

        result["rrf_score"] = score

        result["dense_rank"] = component_ranks[chunk_id].get("dense")
        result["bm25_rank"] = component_ranks[chunk_id].get("bm25")

        fused_results.append(result)

    return fused_results


# --------------------------------------------------
# HYBRID SEARCH + RERANKING
# --------------------------------------------------

class HybridSearch:

    def __init__(self):

        print("Initializing BM25 search...")

        self.bm25 = BM25Search()

        print("Initializing cross-encoder reranker...")

        self.reranker = CrossEncoderReranker()

        print("Hybrid retrieval initialized.")

    def search(self, query: str, top_k: int = DEFAULT_TOP_K):

        if not query or not query.strip():
            raise ValueError("Query cannot be empty.")

        if not isinstance(top_k, int) or not 1 <= top_k <= 100:
            raise ValueError("top_k must be between 1 and 100.")

        # 1. Dense retrieval
        dense_results = semantic_search(
            query=query,
            top_k=CANDIDATE_COUNT,
        )

        # 2. BM25 retrieval
        bm25_results = self.bm25.search(
            query=query,
            top_k=CANDIDATE_COUNT,
        )

        print("\n========== DENSE TOP 10 ==========")

        for rank, result in enumerate(dense_results[:10], 1):
            print(rank, result["chunk_id"])

        print("\n========== BM25 TOP 10 ==========")

        for rank, result in enumerate(bm25_results[:10], 1):
            print(rank, result["chunk_id"])

        # 3. Reciprocal Rank Fusion
        fused_results = reciprocal_rank_fusion(
            ranked_lists=[
                ("dense", dense_results),
                ("bm25", bm25_results),
            ],
            top_k=CANDIDATE_COUNT,
        )

        print(
            f"\nRRF generated {len(fused_results)} candidates."
        )

        # 4. Cross-encoder reranking
        reranked_results = self.reranker.rerank(
            query=query,
            documents=fused_results,
            top_k=top_k,
        )

        return reranked_results


# --------------------------------------------------
# DISPLAY RESULTS
# --------------------------------------------------

def main():

    search_engine = HybridSearch()

    query = input("\nEnter your question: ").strip()

    if not query:
        print("\nPlease enter a valid question.")
        return

    results = search_engine.search(
        query=query,
        top_k=CANDIDATE_COUNT,
    )

    print("\n========== HYBRID + RERANKED RESULTS ==========")

    for rank, result in enumerate(results, start=1):

        print(f"\nRank: {rank}")

        print("Chunk:", result["chunk_id"])
        print("Document:", result["document_id"])
        print("Source:", result["source_file"])
        print("Page:", result["page_number"])

        print("Dense Rank:", result["dense_rank"])
        print("BM25 Rank:", result["bm25_rank"])

        print("RRF Score:", round(result["rrf_score"], 6))
        print("Rerank Score:", round(result["rerank_score"], 4))

        print("Content:", result["text"][:600])

        print("-" * 70)


if __name__ == "__main__":
    main()
