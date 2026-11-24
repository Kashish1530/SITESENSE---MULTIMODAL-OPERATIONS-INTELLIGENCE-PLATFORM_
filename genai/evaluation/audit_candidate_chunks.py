
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

CHUNKS_FILE = ROOT / "data" / "extracted" / "chunks.json"
DATASET_FILE = ROOT / "genai" / "evaluation" / "retrieval_dataset.json"

CANDIDATES = {
    "Q005": [
        "WHP-019-P01-C01",
        "WHP-019-P02-C01",
        "WHP-019-P02-C02",
        "WHP-019-P03-C01",
        "WHP-019-P03-C02",
        "WHP-019-P03-C03",
        "WHP-019-P04-C01",
        "SHB-10-P02-C01",
    ],
    "Q006": [
        "SHB-05-P02-C01",
        "SHB-05-P03-C01",
        "SHB-05-P03-C02",
        "SHB-05-P03-C03",
        "SHB-05-P04-C01",
        "WHP-007-P02-C01",
        "WHP-007-P02-C02",
        "SHB-09-P02-C01",
    ],
}


def load_json(path):
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def main():
    chunks_data = load_json(CHUNKS_FILE)
    dataset = load_json(DATASET_FILE)

    chunks = {
        item["chunk_id"]: item
        for item in chunks_data["chunks"]
    }

    queries = {
        item["query_id"]: item
        for item in dataset["queries"]
    }

    for query_id, candidate_ids in CANDIDATES.items():
        query_data = queries[query_id]
        relevant = query_data["relevant_chunks"]

        print("\n" + "=" * 90)
        print(query_id, "-", query_data["query"])
        print("=" * 90)

        for chunk_id in candidate_ids:
            chunk = chunks.get(chunk_id)

            if chunk is None:
                print(f"\nMISSING CHUNK: {chunk_id}")
                continue

            current_grade = relevant.get(chunk_id, 0)

            print("\n" + "-" * 90)
            print("Chunk ID:", chunk_id)
            print("Document:", chunk["document_id"])
            print("Page:", chunk["page_number"])
            print("Current relevance grade:", current_grade)
            print("\nCONTENT:\n")
            print(chunk["text"])

    print("\nAUDIT INSPECTION COMPLETED")


if __name__ == "__main__":
    main()
