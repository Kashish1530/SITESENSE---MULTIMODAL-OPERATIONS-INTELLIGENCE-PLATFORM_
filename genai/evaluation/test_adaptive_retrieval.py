
from genai.retrieval.hybrid_search import HybridSearch


def main():

    search_engine = HybridSearch()

    test_cases = [
        {
            "id": "Q001",
            "query": "What are the safety rules for forklift operators?",
            "strategy": "KEYWORD_FOCUSED",
        },
        {
            "id": "Q002",
            "query": "How should warehouse PPE be selected and maintained?",
            "strategy": "EXPANDED",
        },
        {
            "id": "Q003",
            "query": "What should workers do during an emergency evacuation?",
            "strategy": "STANDARD",
        },
        {
            "id": "Q004",
            "query": "What precautions apply to electrical work and damaged equipment?",
            "strategy": "EXPANDED",
        },
        {
            "id": "Q005",
            "query": "How should workplace incidents and near misses be reported?",
            "strategy": "EXPANDED",
        },
        {
            "id": "Q006",
            "query": "What precautions should workers follow when handling chemicals?",
            "strategy": "EXPANDED",
        },
        {
            "id": "Q007",
            "query": "How should workers safely handle and move heavy materials?",
            "strategy": "STANDARD",
        },
        {
            "id": "Q008",
            "query": "How should pedestrian routes be kept clear?",
            "strategy": "STANDARD",
        },
    ]

    print("\n" + "=" * 75)
    print(" SITESENSE ADAPTIVE RETRIEVAL TEST")
    print("=" * 75)

    for case in test_cases:

        print("\n" + "#" * 75)
        print("TEST:", case["id"])
        print("QUERY:", case["query"])
        print("EXPECTED STRATEGY:", case["strategy"])

        try:

            results = search_engine.search(
                query=case["query"],
                top_k=5,
                strategy=case["strategy"],
            )

            print("\nRESULT COUNT:", len(results))

            for rank, result in enumerate(results, start=1):

                print(f"\nRank: {rank}")
                print("Chunk:", result["chunk_id"])
                print("Document:", result["document_id"])
                print("Page:", result["page_number"])
                print("Strategy:", result["retrieval_strategy"])
                print("RRF:", round(result["rrf_score"], 6))
                print("Rerank:", round(result["rerank_score"], 4))

            if not results:
                print("WARNING: No retrieval results returned.")

        except Exception as exc:

            print("\nERROR:", repr(exc))
            raise

    print("\n" + "=" * 75)
    print(" ADAPTIVE RETRIEVAL TEST COMPLETED")
    print("=" * 75)


if __name__ == "__main__":
    main()
