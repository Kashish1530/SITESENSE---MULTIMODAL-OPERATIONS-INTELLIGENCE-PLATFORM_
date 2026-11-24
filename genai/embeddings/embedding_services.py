
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import torch
from sentence_transformers import SentenceTransformer


# --------------------------------------------------
# PROJECT CONFIGURATION
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_FILE = PROJECT_ROOT / "data" / "extracted" / "chunks.json"

OUTPUT_FILE = PROJECT_ROOT / "data" / "extracted" / "embeddings.json"

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

BATCH_SIZE = 32

EXPECTED_DIMENSION = 384


# --------------------------------------------------
# DEVICE CONFIGURATION
# --------------------------------------------------

def get_device():
    """
    Select GPU when CUDA is available.
    Otherwise use CPU.
    """

    if torch.cuda.is_available():
        return "cuda"

    return "cpu"


# --------------------------------------------------
# LOAD EMBEDDING MODEL
# --------------------------------------------------

def load_embedding_model():

    device = get_device()

    print(f"Loading model: {MODEL_NAME}")
    print(f"Using device: {device}")

    model = SentenceTransformer(
        MODEL_NAME,
        device=device
    )

    print("Embedding model loaded successfully.")

    return model


# --------------------------------------------------
# LOAD CHUNKS
# --------------------------------------------------

def load_chunks():

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Chunk file not found: {INPUT_FILE}"
        )

    with INPUT_FILE.open("r", encoding="utf-8") as file:
        data = json.load(file)

    chunks = data.get("chunks", [])

    if not chunks:
        raise ValueError("No chunks found in input file.")

    for chunk in chunks:

        if not chunk.get("text", "").strip():
            raise ValueError(
                f"Empty text found in chunk: {chunk.get('chunk_id')}"
            )

    print(f"Loaded {len(chunks)} chunks.")

    return chunks


# --------------------------------------------------
# GENERATE EMBEDDINGS
# --------------------------------------------------

def generate_embeddings(model, chunks):

    texts = [
        chunk["text"]
        for chunk in chunks
    ]

    print("\nGenerating embeddings...")

    vectors = model.encode(
        texts,
        batch_size=BATCH_SIZE,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True
    )

    if vectors.shape[1] != EXPECTED_DIMENSION:
        raise ValueError(
            f"Expected {EXPECTED_DIMENSION} dimensions, "
            f"received {vectors.shape[1]}"
        )

    if not np.isfinite(vectors).all():
        raise ValueError("Non-finite embedding values detected.")

    print("Embedding generation completed.")

    return vectors


# --------------------------------------------------
# ATTACH EMBEDDINGS TO METADATA
# --------------------------------------------------

def build_embedding_records(chunks, vectors):

    records = []

    for chunk, vector in zip(chunks, vectors):

        record = {
            **chunk,
            "embedding": vector.astype(float).tolist()
        }

        records.append(record)

    return records


# --------------------------------------------------
# SAVE EMBEDDINGS
# --------------------------------------------------

def save_embeddings(records):

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    output_data = {

        "model_name": MODEL_NAME,

        "embedding_dimension": EXPECTED_DIMENSION,

        "normalized": True,

        "total_embeddings": len(records),

        "generated_at": datetime.now(
            timezone.utc
        ).isoformat(),

        "embeddings": records

    }

    with OUTPUT_FILE.open("w", encoding="utf-8") as file:

        json.dump(
            output_data,
            file,
            ensure_ascii=False
        )

    print(f"\nEmbeddings saved to: {OUTPUT_FILE}")


# --------------------------------------------------
# MAIN PIPELINE
# --------------------------------------------------

def run_embedding_pipeline():

    print("=" * 55)
    print("SITESENSE EMBEDDING GENERATION")
    print("=" * 55)

    chunks = load_chunks()

    model = load_embedding_model()

    vectors = generate_embeddings(
        model,
        chunks
    )

    records = build_embedding_records(
        chunks,
        vectors
    )

    save_embeddings(records)

    # Validate embedding dimensions and normalization
    first_vector = vectors[0]

    vector_norm = np.linalg.norm(first_vector)

    print("\n" + "=" * 55)
    print("EMBEDDING SUMMARY")
    print("=" * 55)

    print(f"Model             : {MODEL_NAME}")
    print(f"Total embeddings  : {len(records)}")
    print(f"Vector dimensions : {vectors.shape[1]}")
    print(f"First vector size : {len(first_vector)}")
    print(f"First vector norm : {vector_norm:.4f}")
    print(f"Output file       : {OUTPUT_FILE}")

    print("\nEmbedding pipeline completed successfully.")


if __name__ == "__main__":
    run_embedding_pipeline()
