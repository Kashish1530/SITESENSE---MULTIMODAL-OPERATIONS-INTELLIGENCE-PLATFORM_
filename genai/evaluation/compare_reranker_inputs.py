
from pathlib import Path

from sentence_transformers import CrossEncoder

from genai.evaluation.inspect_reranking_failures import TARGETS
import json


PROJECT_ROOT = Path(__file__).resolve().parents[2]

CHUNKS_FILE = (
    PROJECT_ROOT
    / "data"
    / "extracted"
    / "chunks.json"
)

MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L-6-v2"

QUERIES = {
    "Q007 - Manual handling":
        "What are the safe manual handling procedures for warehouse workers?",

    "Q002 - PPE":
        "What are the requirements for selecting, inspecting, wearing and replacing PPE?",
}


def load_chunks():

    with open(CHUNKS_FILE, "r", encoding="utf-8") as file:
        data = json.load(file)

    return {
        chunk["chunk_id"]: chunk
        for chunk in data["chunks"]
    }


def prepare_metadata_content(chunk):

    return (
        f"Document ID: {chunk['document_id']}\n"
        f"Source: {chunk['source_file']}\n"
        f"Page: {chunk['page_number']}\n"
        f"Content: {chunk['text']}"
    )


def main():

    chunks = load_chunks()

    print("Loading cross-encoder...")
    model = CrossEncoder(MODEL_NAME, max_length=512)

    print("\nSITESENSE RERANKER INPUT COMPARISON")
    print("=" * 90)

    for topic, chunk_ids in TARGETS.items():

        query = QUERIES[topic]

        candidates = []

        for chunk_id in chunk_ids:

            chunk = chunks.get(chunk_id)

            if chunk is None:
                continue

            candidates.append((chunk_id, chunk))

        content_pairs = [
            (query, chunk["text"])
            for _, chunk in candidates
        ]

        metadata_pairs = [
            (query, prepare_metadata_content(chunk))
            for _, chunk in candidates
        ]

        content_scores = model.predict(
            content_pairs,
            batch_size=8
        )

        metadata_scores = model.predict(
            metadata_pairs,
            batch_size=8
        )

        print(f"\n\n{topic}")
        print("=" * 90)

        results = []

        for index, (chunk_id, chunk) in enumerate(candidates):

            results.append({
                "chunk_id": chunk_id,
                "content_score": float(content_scores[index]),
                "metadata_score": float(metadata_scores[index]),
            })

        print("\nCONTENT-ONLY RANKING")

        for rank, result in enumerate(
            sorted(
                results,
                key=lambda item: item["content_score"],
                reverse=True
            ),
            start=1
        ):

            print(
                f"{rank:2}. {result['chunk_id']} "
                f"| Score: {result['content_score']:.4f}"
            )

        print("\nMETADATA + CONTENT RANKING")

        for rank, result in enumerate(
            sorted(
                results,
                key=lambda item: item["metadata_score"],
                reverse=True
            ),
            start=1
        ):

            print(
                f"{rank:2}. {result['chunk_id']} "
                f"| Score: {result['metadata_score']:.4f}"
            )


if __name__ == "__main__":
    main()
