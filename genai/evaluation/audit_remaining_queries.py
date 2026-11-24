
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

CHUNKS_FILE = ROOT / "data" / "extracted" / "chunks.json"
DATASET_FILE = ROOT / "genai" / "evaluation" / "retrieval_dataset.json"

TARGET_QUERIES = ["Q001", "Q002", "Q003", "Q004", "Q007", "Q008"]


def load_json(path):
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def main():
    chunks_data = load_json(CHUNKS_FILE)
    dataset = load_json(DATASET_FILE)

    chunks = {
        chunk["chunk_id"]: chunk
        for chunk in chunks_data["chunks"]
    }

    for query_data in dataset["queries"]:
        query_id = query_data["query_id"]

        if query_id not in TARGET_QUERIES:
            continue

        print("\n" + "=" * 100)
        print(f"{query_id}: {query_data['query']}")
        print("=" * 100)

        relevant = query_data["relevant_chunks"]

        for chunk_id, grade in relevant.items():
            chunk = chunks.get(chunk_id)

            if chunk is None:
                print(f"\nMISSING: {chunk_id}")
                continue

            print("\n" + "-" * 100)
            print(f"Chunk: {chunk_id}")
            print(f"Current grade: {grade}")
            print(f"Document: {chunk['document_id']}")
            print(f"Page: {chunk['page_number']}")
            print("\nCONTENT:\n")
            print(chunk["text"])

    print("\nREMAINING QUERY AUDIT COMPLETED")


if __name__ == "__main__":
    main()
