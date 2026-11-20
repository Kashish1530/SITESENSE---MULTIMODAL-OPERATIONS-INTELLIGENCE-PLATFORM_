
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

CHUNKS_FILE = (
    PROJECT_ROOT
    / "data"
    / "extracted"
    / "chunks.json"
)

with open(CHUNKS_FILE, "r", encoding="utf-8") as file:
    data = json.load(file)

chunks = data["chunks"]

print(f"\nTotal chunks: {len(chunks)}")

keywords = [
    "forklift",
    "fire",
    "emergency",
    "evacuation",
    "personal protective equipment",
    "PPE",
    "manual handling",
    "working at height",
    "electrical",
    "incident",
    "near miss",
    "machinery",
    "chemical",
    "pedestrian",
    "maintenance",
    "storage",
]

for keyword in keywords:

    matches = []

    for chunk in chunks:

        if keyword.lower() in chunk["text"].lower():

            matches.append(chunk)

    print("\n" + "=" * 75)
    print(f"KEYWORD: {keyword}")
    print(f"MATCHES: {len(matches)}")
    print("=" * 75)

    for chunk in matches[:5]:

        print("\nChunk ID:", chunk["chunk_id"])
        print("Document:", chunk["document_id"])
        print("Page:", chunk["page_number"])
        print("Content:")
        print(chunk["text"])
        print("-" * 75)
