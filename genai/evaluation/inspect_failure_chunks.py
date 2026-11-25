
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

DATASET_FILE = ROOT / "genai/evaluation/retrieval_dataset.json"
CHUNKS_FILE = ROOT / "data/extracted/chunks.json"

TARGET_QUERIES = {"Q003", "Q005", "Q006", "Q007"}

with open(DATASET_FILE, encoding="utf-8") as f:
    dataset = json.load(f)

with open(CHUNKS_FILE, encoding="utf-8") as f:
    chunks_data = json.load(f)

chunk_lookup = {
    chunk["chunk_id"]: chunk
    for chunk in chunks_data["chunks"]
}

print("\nSITESENSE: RELEVANCE LABEL INSPECTION")
print("=" * 85)

for query_data in dataset["queries"]:

    query_id = query_data["query_id"]

    if query_id not in TARGET_QUERIES:
        continue

    print("\n" + "=" * 85)
    print(f"{query_id}: {query_data['query']}")
    print("=" * 85)

    for chunk_id, grade in query_data["relevant_chunks"].items():

        chunk = chunk_lookup.get(chunk_id)

        print("\n" + "-" * 85)
        print(f"Chunk ID: {chunk_id}")
        print(f"Relevance grade: {grade}")

        if chunk is None:
            print("ERROR: CHUNK NOT FOUND IN INDEXED JSON")
            continue

        print(f"Document: {chunk.get('document_id')}")
        print(f"Page: {chunk.get('page_number')}")
        print(f"Chunk index: {chunk.get('chunk_index')}")

        content = chunk.get("text") or chunk.get("content", "")

        print("\nCHUNK CONTENT:")
        print(content)

print("\n" + "=" * 85)
print("INSPECTION COMPLETED")
print("=" * 85)
