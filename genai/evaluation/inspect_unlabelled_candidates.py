
import json
from pathlib import Path

from genai.retrieval.pgvector_search import semantic_search
from genai.retrieval.bm25_search import BM25Search

ROOT = Path(__file__).resolve().parents[2]

DATASET_FILE = ROOT / "genai" / "evaluation" / "retrieval_dataset.json"
OUTPUT_FILE = ROOT / "genai" / "evaluation" / "unlabelled_candidates.json"

TARGET_QUERIES = ["Q001", "Q002", "Q003", "Q004", "Q007", "Q008"]

TOP_K = 20


def load_json(path):
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def main():
    dataset = load_json(DATASET_FILE)

    bm25 = BM25Search()

    all_candidates = []

    for item in dataset["queries"]:
        query_id = item["query_id"]

        if query_id not in TARGET_QUERIES:
            continue

        query = item["query"]
        labelled = item["relevant_chunks"]

        print("\n" + "=" * 90)
        print(f"{query_id}: {query}")
        print("=" * 90)

        dense_results = semantic_search(query=query, top_k=TOP_K)
        bm25_results = bm25.search(query=query, top_k=TOP_K)

        candidate_map = {}

        for rank, result in enumerate(dense_results, start=1):
            chunk_id = result["chunk_id"]

            if chunk_id in labelled:
                continue

            candidate_map.setdefault(chunk_id, {
                "chunk_id": chunk_id,
                "dense_rank": None,
                "bm25_rank": None,
                "text": result["text"],
            })

            candidate_map[chunk_id]["dense_rank"] = rank

        for rank, result in enumerate(bm25_results, start=1):
            chunk_id = result["chunk_id"]

            if chunk_id in labelled:
                continue

            candidate_map.setdefault(chunk_id, {
                "chunk_id": chunk_id,
                "dense_rank": None,
                "bm25_rank": None,
                "text": result["text"],
            })

            candidate_map[chunk_id]["bm25_rank"] = rank

        candidates = list(candidate_map.values())

        candidates.sort(
            key=lambda item: (
                min(
                    item["dense_rank"] or 999,
                    item["bm25_rank"] or 999
                )
            )
        )

        print("Unlabelled candidates:", len(candidates))

        for candidate in candidates:
            print("\n" + "-" * 90)
            print("Chunk:", candidate["chunk_id"])
            print("Semantic rank:", candidate["dense_rank"])
            print("BM25 rank:", candidate["bm25_rank"])
            print("\nCONTENT:\n")
            print(candidate["text"])

        all_candidates.append({
            "query_id": query_id,
            "query": query,
            "candidates": candidates,
        })

    with open(OUTPUT_FILE, "w", encoding="utf-8") as file:
        json.dump(
            all_candidates,
            file,
            indent=4,
            ensure_ascii=False
        )

    print("\n" + "=" * 90)
    print("CANDIDATE INSPECTION COMPLETED")
    print("Results saved to:", OUTPUT_FILE)


if __name__ == "__main__":
    main()
