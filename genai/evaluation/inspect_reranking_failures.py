
import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]

CHUNKS_FILE = (
    PROJECT_ROOT
    / "data"
    / "extracted"
    / "chunks.json"
)


TARGETS = {
    "Q007 - Manual handling": [
        "SHB-06-P02-C01",
        "SHB-06-P03-C01",
        "SHB-06-P03-C02",
        "SHB-06-P03-C03",
        "WHP-007-P02-C02",
        "WHP-007-P02-C01",
        "WHP-016-P02-C01",
        "WHP-002-P02-C01",
    ],

    "Q002 - PPE": [
        "WHP-003-P02-C01",
        "WHP-003-P02-C02",
        "SHB-02-P02-C01",
        "WHP-003-P04-C01",
        "SHB-02-P04-C01",
        "SHB-02-P01-C01",
        "SHB-05-P02-C01",
    ],
}


def main():

    with open(CHUNKS_FILE, "r", encoding="utf-8") as file:
        data = json.load(file)

    chunks = {
        chunk["chunk_id"]: chunk
        for chunk in data["chunks"]
    }

    print("\nSITESENSE RERANKING FAILURE INSPECTION")
    print("=" * 85)

    for topic, chunk_ids in TARGETS.items():

        print(f"\n\n{topic}")
        print("=" * 85)

        for chunk_id in chunk_ids:

            chunk = chunks.get(chunk_id)

            if chunk is None:
                print(f"\nNOT FOUND: {chunk_id}")
                continue

            print(f"\nChunk ID : {chunk_id}")
            print(f"Document : {chunk['document_id']}")
            print(f"Source   : {chunk['source_file']}")
            print(f"Page     : {chunk['page_number']}")

            print("\nCONTENT")
            print("-" * 85)
            print(chunk["text"])
            print("-" * 85)


if __name__ == "__main__":
    main()
