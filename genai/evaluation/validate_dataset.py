
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

DATASET_FILE = ROOT / "genai/evaluation/retrieval_dataset.json"
CHUNKS_FILE = ROOT / "data/extracted/chunks.json"

with open(DATASET_FILE, encoding="utf-8") as f:
    dataset = json.load(f)

with open(CHUNKS_FILE, encoding="utf-8") as f:
    chunks_data = json.load(f)

available_ids = {
    chunk["chunk_id"]
    for chunk in chunks_data["chunks"]
}

missing = []

for query in dataset["queries"]:

    for chunk_id in query["relevant_chunks"]:

        if chunk_id not in available_ids:
            missing.append((query["query_id"], chunk_id))

print("\nSITESENSE DATASET VALIDATION")
print("=" * 50)

print("Total queries:", len(dataset["queries"]))
print("Total indexed chunks:", len(available_ids))

labelled_count = sum(
    len(q["relevant_chunks"])
    for q in dataset["queries"]
)

print("Total labelled chunks:", labelled_count)
print("Missing chunk references:", len(missing))

if missing:

    print("\nMISSING CHUNKS:")

    for query_id, chunk_id in missing:
        print(query_id, "->", chunk_id)

    raise SystemExit("\nVALIDATION FAILED")

print("\nVALIDATION PASSED")
