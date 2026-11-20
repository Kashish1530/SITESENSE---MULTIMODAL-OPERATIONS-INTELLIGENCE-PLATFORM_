
import json
import re
from pathlib import Path

from rank_bm25 import BM25Okapi


PROJECT_ROOT = Path(__file__).resolve().parents[2]

CHUNKS_FILE = (
    PROJECT_ROOT / "data" / "extracted" / "chunks.json"
)


def tokenize(text: str):
    """Basic lowercase word tokenizer."""
    return re.findall(r"[a-z0-9]+", text.lower())


def load_chunks():

    with open(CHUNKS_FILE, "r", encoding="utf-8") as file:
        data = json.load(file)

    return data["chunks"]


class BM25Search:

    def __init__(self):

        self.chunks = load_chunks()

        self.tokenized_corpus = [
            tokenize(chunk["text"])
            for chunk in self.chunks
        ]

        self.bm25 = BM25Okapi(self.tokenized_corpus)

        print(f"BM25 indexed {len(self.chunks)} chunks.")

    def search(self, query: str, top_k: int = 5):

        if not query or not query.strip():
            raise ValueError("Query cannot be empty.")

        if not isinstance(top_k, int) or not 1 <= top_k <= 100:
            raise ValueError("top_k must be between 1 and 100.")

        query_tokens = tokenize(query)

        scores = self.bm25.get_scores(query_tokens)

        ranked_indices = sorted(
            range(len(scores)),
            key=lambda index: scores[index],
            reverse=True
        )

        results = []

        for index in ranked_indices[:top_k]:

            chunk = self.chunks[index]

            results.append({
                "chunk_id": chunk["chunk_id"],
                "document_id": chunk["document_id"],
                "document_type": chunk["document_type"],
                "source_file": chunk["source_file"],
                "page_number": chunk["page_number"],
                "text": chunk["text"],
                "bm25_score": float(scores[index])
            })

        return results


def main():

    search_engine = BM25Search()

    query = input("\nEnter your question: ").strip()

    results = search_engine.search(query, top_k=5)

    print("\n========== BM25 SEARCH RESULTS ==========")

    for rank, result in enumerate(results, start=1):

        print(f"\nRank: {rank}")
        print("Chunk:", result["chunk_id"])
        print("Document:", result["document_id"])
        print("Page:", result["page_number"])
        print("BM25 Score:", round(result["bm25_score"], 4))
        print("Content:", result["text"][:500])

        print("-" * 70)


if __name__ == "__main__":
    main()
