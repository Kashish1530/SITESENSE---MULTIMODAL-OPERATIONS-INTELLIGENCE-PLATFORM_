
from genai.retrieval.pgvector_search import (
    generate_query_embedding,
    get_connection,
)

QUERY = "What are the safety rules for forklift operators?"

TARGET_DOCUMENTS = ["WHP-006", "SHB-03"]


def main():

    embedding = generate_query_embedding(QUERY)

    vector_string = (
        "[" + ",".join(str(float(x)) for x in embedding) + "]"
    )

    connection = get_connection()

    try:
        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT
                    chunk_id,
                    document_id,
                    source_file,
                    page_number,
                    1 - (embedding <=> %s::vector) AS similarity,
                    content
                FROM document_chunks
                WHERE document_id IN (%s, %s)
                ORDER BY embedding <=> %s::vector
                LIMIT 10;
                """,
                (
                    vector_string,
                    TARGET_DOCUMENTS[0],
                    TARGET_DOCUMENTS[1],
                    vector_string,
                ),
            )

            results = cursor.fetchall()

            print("\n====== TARGET DOCUMENT RETRIEVAL ======")

            for rank, row in enumerate(results, start=1):

                print(f"\nRank: {rank}")
                print("Chunk:", row[0])
                print("Document:", row[1])
                print("Source:", row[2])
                print("Page:", row[3])
                print("Similarity:", round(float(row[4]), 4))
                print("Content:", row[5][:700])

                print("-" * 70)

    finally:
        connection.close()


if __name__ == "__main__":
    main()
