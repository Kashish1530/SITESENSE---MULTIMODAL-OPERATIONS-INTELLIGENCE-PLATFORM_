
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

CHUNKS_FILE = (
    PROJECT_ROOT
    / "data"
    / "extracted"
    / "chunks.json"
)

TARGET_DOCUMENTS = [
    "WHP-003",  # PPE
    "WHP-007",  # Chemical safety
    "WHP-008",  # Fire safety
    "WHP-009",  # Emergency response
    "WHP-015",  # Electrical safety
    "WHP-019",  # Incident reporting
    "SHB-05",   # Chemical handling
    "SHB-06",   # Manual handling
    "SHB-03",   # Forklift safety
]

with open(CHUNKS_FILE, "r", encoding="utf-8") as file:
    data = json.load(file)

chunks = data["chunks"]

print("\nSITESENSE TOPIC CHUNK INSPECTION")
print("=" * 85)

for document_id in TARGET_DOCUMENTS:

    document_chunks = [
        chunk
        for chunk in chunks
        if chunk["document_id"] == document_id
    ]

    print("\n" + "#" * 85)
    print(f"DOCUMENT: {document_id}")
    print(f"TOTAL CHUNKS: {len(document_chunks)}")
    print("#" * 85)

    for chunk in document_chunks:

        print("\nChunk ID:", chunk["chunk_id"])
        print("Page:", chunk["page_number"])
        print("Chunk index:", chunk["chunk_index"])
        print("-" * 75)
        print(chunk["text"])
        print("-" * 75)
