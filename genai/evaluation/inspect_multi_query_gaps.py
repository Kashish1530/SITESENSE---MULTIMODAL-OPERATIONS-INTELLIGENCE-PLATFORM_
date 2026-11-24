
import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]

CHUNKS_FILE = (
    PROJECT_ROOT
    / "data"
    / "extracted"
    / "chunks.json"
)

TARGET_CHUNKS = {
    "Q005": [
        "WHP-019-P03-C03",
        "WHP-019-P04-C01",
    ],
    "Q006": [
        "SHB-05-P03-C01",
        "SHB-05-P03-C03",
    ],
}


def main():

    with open(CHUNKS_FILE, "r", encoding="utf-8") as file:
        data = json.load(file)

    chunks = {
        chunk["chunk_id"]: chunk
        for chunk in data["chunks"]
    }

    print("\nSITESENSE MULTI-QUERY RETRIEVAL GAP INSPECTION")
    print("=" * 75)

    for query_id, chunk_ids in TARGET_CHUNKS.items():

        print(f"\n{query_id}")
        print("=" * 75)

        for chunk_id in chunk_ids:

            chunk = chunks.get(chunk_id)

            if chunk is None:
                print(f"\nNOT FOUND: {chunk_id}")
                continue

            print(f"\nChunk ID: {chunk['chunk_id']}")
            print(f"Document: {chunk['document_id']}")
            print(f"Source: {chunk['source_file']}")
            print(f"Page: {chunk['page_number']}")

            print("\nCONTENT")
            print("-" * 75)
            print(chunk["text"])
            print("-" * 75)


if __name__ == "__main__":
    main()
