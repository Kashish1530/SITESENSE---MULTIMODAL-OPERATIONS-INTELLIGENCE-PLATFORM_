
import json
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer


PROJECT_ROOT = Path(__file__).resolve().parents[2]

EMBEDDING_FILE = (
    PROJECT_ROOT / "data" / "extracted" / "embeddings.json"
)

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

TOP_K = 5


def load_data():

    with EMBEDDING_FILE.open("r", encoding="utf-8") as file:
        data = json.load(file)

    records = data["embeddings"]

    texts = [record["text"] for record in records]

    vectors = np.asarray(
        [record["embedding"] for record in records],
        dtype=np.float32
    )

    return records, texts, vectors


def semantic_search(query, model, records, vectors, top_k=TOP_K):

    query_vector = model.encode(
        query,
        convert_to_numpy=True,
        normalize_embeddings=True
    )

    # Normalized vectors allow dot product to calculate cosine similarity.
    scores = vectors @ query_vector

    top_indices = np.argsort(scores)[::-1][:top_k]

    results = []

    for index in top_indices:

        result = {
            "chunk_id": records[index]["chunk_id"],
            "document_id": records[index]["document_id"],
            "document_type": records[index]["document_type"],
            "source_file": records[index]["source_file"],
            "page_number": records[index]["page_number"],
            "similarity_score": float(scores[index]),
            "text": records[index]["text"]
        }

        results.append(result)

    return results


def main():

    print("Loading embedded documents...")

    records, texts, vectors = load_data()

    print(f"Loaded {len(records)} embeddings.")
    print(f"Vector matrix shape: {vectors.shape}")

    print("\nLoading embedding model...")

    model = SentenceTransformer(MODEL_NAME)

    while True:

        query = input(
            "\nEnter your question (or type 'exit'): "
        ).strip()

        if query.lower() == "exit":
            break

        if not query:
            continue

        results = semantic_search(
            query,
            model,
            records,
            vectors
        )

        print("\n" + "=" * 60)
        print("TOP MATCHING DOCUMENT CHUNKS")
        print("=" * 60)

        for rank, result in enumerate(results, start=1):

            print(f"\nRank: {rank}")
            print(f"Chunk ID: {result['chunk_id']}")
            print(f"Document: {result['document_id']}")
            print(f"Page: {result['page_number']}")
            print(
                f"Similarity: "
                f"{result['similarity_score']:.4f}"
            )
            print(f"Text: {result['text'][:500]}")
            print("-" * 60)


if __name__ == "__main__":
    main()
