
import os
from pathlib import Path

import psycopg2
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer


# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]

load_dotenv(PROJECT_ROOT / ".env")

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

model = SentenceTransformer(MODEL_NAME)


# --------------------------------------------------
# DATABASE CONNECTION
# --------------------------------------------------

def get_connection():

    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        connect_timeout=10,
    )


# --------------------------------------------------
# QUERY EMBEDDING
# --------------------------------------------------

def generate_query_embedding(query: str):

    if not query or not query.strip():
        raise ValueError("Search query cannot be empty.")

    embedding = model.encode(
        query,
        normalize_embeddings=True
    )

    return embedding.tolist()


# --------------------------------------------------
# SEMANTIC SEARCH
# --------------------------------------------------

def semantic_search(
    query: str,
    top_k: int = 5,
    document_type: str | None = None
):

    if not isinstance(top_k, int) or not 1 <= top_k <= 100:
        raise ValueError("top_k must be an integer between 1 and 100.")

    query_vector = generate_query_embedding(query)

    vector_string = (
        "[" + ",".join(str(float(x)) for x in query_vector) + "]"
    )

    sql = """
        SELECT
            chunk_id,
            document_id,
            document_type,
            source_file,
            page_number,
            chunk_index,
            content,
            1 - (embedding <=> %s::vector) AS similarity
        FROM document_chunks
    """

    params = [vector_string]

    if document_type is not None:
        if document_type not in ("policy", "handbook"):
            raise ValueError(
                "document_type must be 'policy', 'handbook', or None."
            )

        sql += " WHERE document_type = %s"
        params.append(document_type)

    sql += """
        ORDER BY embedding <=> %s::vector
        LIMIT %s;
    """

    params.extend([vector_string, top_k])

    connection = None

    try:

        connection = get_connection()

        with connection.cursor() as cursor:

            cursor.execute(sql, params)

            rows = cursor.fetchall()

        results = []

        for row in rows:

            results.append({
                "chunk_id": row[0],
                "document_id": row[1],
                "document_type": row[2],
                "source_file": row[3],
                "page_number": row[4],
                "chunk_index": row[5],
                "text": row[6],
                "similarity": float(row[7]),
            })

        return results

    finally:

        if connection:
            connection.close()


# --------------------------------------------------
# DISPLAY RESULTS
# --------------------------------------------------

def main():

    query = input("\nEnter your question: ").strip()

    results = semantic_search(
        query=query,
        top_k=5
    )

    print("\n========== SEARCH RESULTS ==========")

    for index, result in enumerate(results, start=1):

        print(f"\nRank: {index}")
        print("Chunk ID:", result["chunk_id"])
        print("Document:", result["document_id"])
        print("Source:", result["source_file"])
        print("Page:", result["page_number"])
        print("Similarity:", round(result["similarity"], 4))
        print("Content:", result["text"][:500])
        print("-" * 70)


if __name__ == "__main__":
    main()
