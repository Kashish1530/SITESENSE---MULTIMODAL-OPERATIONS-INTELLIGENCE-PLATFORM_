
from genai.retrieval.pgvector_search import semantic_search
from genai.retrieval.bm25_search import BM25Search
from genai.retrieval.hybrid_search import reciprocal_rank_fusion


TARGET_QUERIES = {
    "Q005": "How should workplace incidents and near misses be reported?",
    "Q006": "What precautions should workers follow when handling chemicals?",
}

TOP_K = 15


def print_results(title, results, score_key):
    print(f"\n{title}")
    print("=" * 110)

    for rank, result in enumerate(results, start=1):

        chunk_id = result.get("chunk_id", "N/A")
        document_id = result.get("document_id", "N/A")
        page_number = result.get("page_number", "N/A")
        score = result.get(score_key, "N/A")

        # Both retrieval functions return chunk text under "text".
        content = " ".join(result.get("text", "").split())

        print(f"\nRank: {rank}")
        print(f"Chunk: {chunk_id}")
        print(f"Document: {document_id}")
        print(f"Page: {page_number}")
        print(f"Score: {score}")
        print(f"Content: {content[:700]}")

        print("-" * 110)


def main():

    print("\nInitializing BM25...")
    bm25 = BM25Search()

    for query_id, question in TARGET_QUERIES.items():

        print("\n\n" + "#" * 110)
        print(f"{query_id}: {question}")
        print("#" * 110)

        # 1. Semantic retrieval
        semantic_results = semantic_search(
            query=question,
            top_k=TOP_K
        )

        # 2. BM25 retrieval
        bm25_results = bm25.search(
            query=question,
            top_k=TOP_K
        )

        # 3. Reciprocal Rank Fusion
        rrf_results = reciprocal_rank_fusion(
            ranked_lists=[
                ("dense", semantic_results),
                ("bm25", bm25_results)
            ],
            top_k=TOP_K,
            rrf_k=60
        )

        # Print all three retrieval stages
        print_results(
            "SEMANTIC TOP 15",
            semantic_results,
            "similarity"
        )

        print_results(
            "BM25 TOP 15",
            bm25_results,
            "bm25_score"
        )

        print_results(
            "RRF TOP 15",
            rrf_results,
            "rrf_score"
        )

    print("\n" + "#" * 110)
    print("WEAK QUERY CANDIDATE INSPECTION COMPLETED")
    print("#" * 110)


if __name__ == "__main__":
    main()
