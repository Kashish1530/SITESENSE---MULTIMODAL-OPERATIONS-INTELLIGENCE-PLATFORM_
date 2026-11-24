
import json
import os
from pathlib import Path

import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv


# --------------------------------------------------
# 1. PROJECT CONFIGURATION
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]

EMBEDDINGS_FILE = (
    PROJECT_ROOT / "data" / "extracted" / "embeddings.json"
)

load_dotenv(PROJECT_ROOT / ".env")

BATCH_SIZE = 50
EXPECTED_DIMENSION = 384


# --------------------------------------------------
# 2. DATABASE CONNECTION
# --------------------------------------------------

def get_database_connection():
    """Create a PostgreSQL connection using environment variables."""

    required_variables = [
        "DB_HOST",
        "DB_PORT",
        "DB_NAME",
        "DB_USER",
        "DB_PASSWORD",
    ]

    missing = [
        key for key in required_variables
        if not os.getenv(key)
    ]

    if missing:
        raise ValueError(
            f"Missing database environment variables: {missing}"
        )

    connection = psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        connect_timeout=10,
    )

    return connection


# --------------------------------------------------
# 3. LOAD EMBEDDINGS JSON
# --------------------------------------------------

def load_embeddings():
    """Load and validate embedding records."""

    if not EMBEDDINGS_FILE.exists():
        raise FileNotFoundError(
            f"Embeddings file not found: {EMBEDDINGS_FILE}"
        )

    with open(EMBEDDINGS_FILE, "r", encoding="utf-8") as file:
        data = json.load(file)

    records = data.get("embeddings", [])

    if not records:
        raise ValueError("No embeddings found.")

    if data.get("embedding_dimension") != EXPECTED_DIMENSION:
        raise ValueError("Unexpected embedding dimension.")

    if data.get("total_embeddings") != len(records):
        raise ValueError("Embedding count does not match metadata.")

    seen_ids = set()

    for record in records:
        chunk_id = record["chunk_id"]
        vector = record["embedding"]

        if chunk_id in seen_ids:
            raise ValueError(f"Duplicate chunk ID: {chunk_id}")

        seen_ids.add(chunk_id)

        if len(vector) != EXPECTED_DIMENSION:
            raise ValueError(
                f"Invalid vector dimensions for {chunk_id}"
            )

        if not all(
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and __import__("math").isfinite(value)
            for value in vector
        ):
            raise ValueError(
                f"Invalid vector values for {chunk_id}"
            )

        if not record.get("text"):
            raise ValueError(f"Empty text for {chunk_id}")

    print(f"Validated {len(records)} embedding records.")

    return records


# --------------------------------------------------
# 4. INSERT RECORDS INTO POSTGRESQL
# --------------------------------------------------

def insert_embeddings(connection, records):
    """Insert embeddings in batches with duplicate protection."""

    query = """
        INSERT INTO document_chunks (
            chunk_id,
            document_id,
            document_type,
            source_file,
            page_number,
            chunk_index,
            content,
            embedding
        )
        VALUES %s
        ON CONFLICT (chunk_id) DO NOTHING;
    """

    inserted_before = get_record_count(connection)

    with connection.cursor() as cursor:

        for start in range(0, len(records), BATCH_SIZE):
            batch = records[start:start + BATCH_SIZE]

            values = [
                (
                    record["chunk_id"],
                    record["document_id"],
                    record["document_type"],
                    record["source_file"],
                    record["page_number"],
                    record["chunk_index"],
                    record["text"],
                    "[" + ",".join(
                        str(float(value))
                        for value in record["embedding"]
                    ) + "]",
                )
                for record in batch
            ]

            execute_values(
                cursor,
                query,
                values,
                template="(%s, %s, %s, %s, %s, %s, %s, %s::vector)",
                page_size=BATCH_SIZE,
            )

            connection.commit()

            print(
                f"Processed {min(start + BATCH_SIZE, len(records))}"
                f"/{len(records)} records."
            )

    inserted_after = get_record_count(connection)

    return inserted_after - inserted_before


# --------------------------------------------------
# 5. DATABASE VALIDATION
# --------------------------------------------------

def get_record_count(connection):
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT COUNT(*) FROM document_chunks;"
        )
        return cursor.fetchone()[0]


def verify_database(connection):
    """Verify database records and vector dimensions."""

    with connection.cursor() as cursor:

        cursor.execute("""
            SELECT
                COUNT(*),
                COUNT(DISTINCT chunk_id),
                COUNT(DISTINCT document_id)
            FROM document_chunks;
        """)

        total, unique_chunks, documents = cursor.fetchone()

        cursor.execute("""
            SELECT chunk_id, vector_dims(embedding)
            FROM document_chunks
            ORDER BY id
            LIMIT 1;
        """)

        sample = cursor.fetchone()

    print("\n========== DATABASE REPORT ==========")
    print("Total records:", total)
    print("Unique chunks:", unique_chunks)
    print("Unique documents:", documents)
    print("Sample chunk:", sample[0] if sample else "None")
    print("Vector dimensions:", sample[1] if sample else "None")
    print("=====================================")

    if total != unique_chunks:
        raise RuntimeError("Duplicate chunk IDs detected.")

    if sample and sample[1] != EXPECTED_DIMENSION:
        raise RuntimeError("Incorrect vector dimensions.")


# --------------------------------------------------
# 6. MAIN EXECUTION
# --------------------------------------------------

def main():

    connection = None

    try:
        print("Loading embedding records...")

        records = load_embeddings()

        print("\nConnecting to PostgreSQL...")

        connection = get_database_connection()

        print("Database connection successful.")

        inserted = insert_embeddings(connection, records)

        print(f"\nNew records inserted: {inserted}")

        verify_database(connection)

        print("\nDatabase ingestion completed successfully.")

    except Exception:
        if connection:
            connection.rollback()

        raise

    finally:
        if connection:
            connection.close()
            print("Database connection closed.")


if __name__ == "__main__":
    main()
