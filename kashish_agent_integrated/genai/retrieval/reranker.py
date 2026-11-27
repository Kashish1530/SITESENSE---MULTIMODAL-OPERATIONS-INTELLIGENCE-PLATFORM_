
from pathlib import Path

from sentence_transformers import CrossEncoder


class CrossEncoderReranker:
    """
    Reranks retrieved chunks using:
    - User query
    - Document ID
    - Document title/source filename
    - Page number
    - Actual chunk content
    """

    def __init__(
        self,
        model_name="cross-encoder/ms-marco-MiniLM-L-6-v2",
    ):

        print("Loading cross-encoder model...")

        self.model = CrossEncoder(
            model_name,
            max_length=512,
        )

        print("Cross-encoder initialized.")

    @staticmethod
    def prepare_document(document):

        document_id = document.get("document_id", "Unknown")

        source_file = document.get("source_file", "Unknown")

        page_number = document.get("page_number", "Unknown")

        # Convert filename into readable document title.
        source_title = Path(source_file).stem.replace("_", " ")

        content = document.get("text", "")

        return (
            f"Document ID: {document_id}\n"
            f"Document title: {source_title}\n"
            f"Page number: {page_number}\n"
            f"Document content:\n{content}"
        )

    def rerank(
        self,
        query: str,
        documents: list,
        top_k: int = 5,
    ):

        if not query or not query.strip():
            raise ValueError("Query cannot be empty.")

        if not documents:
            return []

        if not isinstance(top_k, int) or not 1 <= top_k <= 100:
            raise ValueError("top_k must be between 1 and 100.")

        # Prepare question-document pairs with metadata.
        pairs = []

        for document in documents:

            document_text = self.prepare_document(document)

            pairs.append((query, document_text))

        # Generate relevance scores.
        scores = self.model.predict(
            pairs,
            show_progress_bar=False,
            batch_size=8,
        )

        reranked_documents = []

        for document, score in zip(documents, scores):

            result = document.copy()

            result["rerank_score"] = float(score)

            reranked_documents.append(result)

        # Highest score first.
        reranked_documents.sort(
            key=lambda item: item["rerank_score"],
            reverse=True,
        )

        return reranked_documents[:top_k]
