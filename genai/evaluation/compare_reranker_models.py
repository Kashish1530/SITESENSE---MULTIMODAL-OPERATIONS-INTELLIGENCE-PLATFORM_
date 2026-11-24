
import json
from pathlib import Path

from sentence_transformers import CrossEncoder


PROJECT_ROOT = Path(__file__).resolve().parents[2]

CHUNKS_FILE = (
    PROJECT_ROOT
    / "data"
    / "extracted"
    / "chunks.json"
)

MODELS = [
    "cross-encoder/ms-marco-MiniLM-L-6-v2",
    "cross-encoder/ms-marco-MiniLM-L-12-v2",
    "BAAI/bge-reranker-base",
]

QUERIES = {
    "Q007 - Manual handling": {
        "query": (
            "What are the safe manual handling procedures "
            "for warehouse workers?"
        ),
        "chunks": [
            "SHB-06-P02-C01",
            "SHB-06-P03-C01",
            "SHB-06-P03-C02",
            "SHB-06-P03-C03",
            "WHP-007-P02-C02",
            "WHP-007-P02-C01",
            "WHP-016-P02-C01",
            "WHP-002-P02-C01",
        ],
    },

    "Q002 - PPE": {
        "query": (
            "What are the requirements for selecting, inspecting, "
            "wearing and replacing PPE?"
        ),
        "chunks": [
            "WHP-003-P02-C01",
            "WHP-003-P02-C02",
            "SHB-02-P02-C01",
            "WHP-003-P04-C01",
            "SHB-02-P04-C01",
            "SHB-02-P01-C01",
            "SHB-05-P02-C01",
        ],
    },
}


def load_chunks():

    with open(CHUNKS_FILE, "r", encoding="utf-8") as file:
        data = json.load(file)

    return {
        chunk["chunk_id"]: chunk
        for chunk in data["chunks"]
    }


def prepare_document(chunk):

    return (
        f"Document ID: {chunk['document_id']}\n"
        f"Source: {chunk['source_file']}\n"
        f"Page: {chunk['page_number']}\n"
        f"Content: {chunk['text']}"
    )


def main():

    chunks = load_chunks()

    for model_name in MODELS:

        print("\n\n")
        print("=" * 100)
        print(f"MODEL: {model_name}")
        print("=" * 100)

        print("\nLoading model...")

        model = CrossEncoder(
            model_name,
            max_length=512
        )

        for topic, config in QUERIES.items():

            query = config["query"]

            candidates = []

            for chunk_id in config["chunks"]:

                chunk = chunks.get(chunk_id)

                if chunk is None:
                    print(f"Missing chunk: {chunk_id}")
                    continue

                candidates.append(
                    (chunk_id, prepare_document(chunk))
                )

            pairs = [
                (query, document)
                for _, document in candidates
            ]

            scores = model.predict(
                pairs,
                batch_size=8
            )

            ranked = sorted(
                zip(candidates, scores),
                key=lambda item: float(item[1]),
                reverse=True
            )

            print(f"\n{topic}")
            print("-" * 100)

            for rank, ((chunk_id, _), score) in enumerate(
                ranked,
                start=1
            ):

                print(
                    f"{rank:2}. {chunk_id:<25} "
                    f"Score: {float(score):.4f}"
                )

        del model

    print("\nMODEL COMPARISON COMPLETED")


if __name__ == "__main__":
    main()
