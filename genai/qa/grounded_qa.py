
import json
import time
import urllib.error
import urllib.request
from typing import Any

from genai.retrieval.hybrid_search import HybridSearch
from genai.qa.prompt_templates import SYSTEM_PROMPT, build_user_prompt


# ============================================================
# CONFIGURATION
# ============================================================

OLLAMA_BASE_URL = "http://localhost:11434"
DEFAULT_MODEL = "qwen2.5:1.5b"

DEFAULT_TOP_K = 5
REQUEST_TIMEOUT = 180
MAX_CONTEXT_CHARS = 14000

INSUFFICIENT_EVIDENCE_PHRASES = [
    "the available documents do not provide sufficient evidence",
    "insufficient evidence to answer",
    "cannot determine from the provided documents",
    "the provided documents do not contain enough information",
    "there is not enough information in the provided documents",
]


# ============================================================
# OLLAMA CLIENT
# ============================================================

class OllamaClient:
    """Communicates with the locally running Ollama API."""

    def __init__(
        self,
        base_url: str = OLLAMA_BASE_URL,
        model: str = DEFAULT_MODEL,
        timeout: int = REQUEST_TIMEOUT,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def check_connection(self) -> bool:
        """Check whether Ollama is running and the model is available."""

        try:
            url = f"{self.base_url}/api/tags"

            request = urllib.request.Request(
                url,
                method="GET",
            )

            with urllib.request.urlopen(
                request,
                timeout=10,
            ) as response:
                data = json.loads(response.read().decode("utf-8"))

            available_models = [
                model.get("name", "")
                for model in data.get("models", [])
            ]

            model_available = any(
                name == self.model
                or name.startswith(f"{self.model}:")
                for name in available_models
            )

            if not model_available:
                print(f"Model not found: {self.model}")
                print("Available models:", available_models)
                return False

            return True

        except Exception as error:
            print(f"Ollama connection failed: {error}")
            return False

    def generate(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        """Generate a non-streaming response from Ollama."""

        url = f"{self.base_url}/api/chat"

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": user_prompt,
                },
            ],
            "stream": False,
            "options": {
                "temperature": 0,
                "num_ctx": 4096,
            },
        }

        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
            },
            method="POST",
        )

        start_time = time.perf_counter()

        try:
            with urllib.request.urlopen(
                request,
                timeout=self.timeout,
            ) as response:
                result = json.loads(
                    response.read().decode("utf-8")
                )

        except urllib.error.URLError as error:
            raise RuntimeError(
                f"Could not connect to Ollama: {error}"
            ) from error

        except TimeoutError as error:
            raise RuntimeError(
                "Ollama request timed out."
            ) from error

        except Exception as error:
            raise RuntimeError(
                f"Ollama generation failed: {error}"
            ) from error

        latency_ms = round(
            (time.perf_counter() - start_time) * 1000,
            2,
        )

        return {
            "answer": result.get("message", {}).get("content", "").strip(),
            "model": result.get("model", self.model),
            "latency_ms": latency_ms,
            "prompt_tokens": result.get("prompt_eval_count", 0),
            "completion_tokens": result.get("eval_count", 0),
            "total_duration_ns": result.get("total_duration", 0),
        }


# ============================================================
# GROUNDED QA ENGINE
# ============================================================

class GroundedQA:
    """
    Retrieval-Augmented Question Answering.

    Pipeline:
        Question
            |
            v
        Hybrid Retrieval
            |
            v
        Context Construction
            |
            v
        Ollama LLM
            |
            v
        Citation Validation
            |
            v
        Grounded Response
    """

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        top_k: int = DEFAULT_TOP_K,
    ):
        if not isinstance(top_k, int) or top_k <= 0:
            raise ValueError("top_k must be a positive integer.")

        self.top_k = top_k

        self.retriever = HybridSearch()

        self.llm = OllamaClient(
            model=model,
        )

        print("\nSITESENSE Grounded QA initialized.")
        print(f"Model: {model}")
        print(f"Top K: {top_k}")

    # --------------------------------------------------------
    # CONTEXT CONSTRUCTION
    # --------------------------------------------------------

    def build_context(
        self,
        results: list[dict[str, Any]],
    ) -> tuple[str, list[dict[str, Any]]]:

        context_parts = []
        sources = []
        current_length = 0

        for index, result in enumerate(results, start=1):

            source_label = f"S{index}"

            source = {
                "label": source_label,
                "chunk_id": result.get("chunk_id"),
                "document_id": result.get("document_id"),
                "document_type": result.get("document_type"),
                "source_file": result.get("source_file"),
                "page_number": result.get("page_number"),
                "retrieval_score": result.get("rerank_score"),
            }

            content = result.get("text", "").strip()

            if not content:
                continue

            passage = (
                f"[{source_label}]\n"
                f"Document: {source['document_id']}\n"
                f"Document Type: {source['document_type']}\n"
                f"Page: {source['page_number']}\n"
                f"Chunk ID: {source['chunk_id']}\n"
                f"Content:\n{content}\n"
            )

            if current_length + len(passage) > MAX_CONTEXT_CHARS:
                break

            context_parts.append(passage)
            sources.append(source)

            current_length += len(passage)

        return "\n---\n".join(context_parts), sources

    # --------------------------------------------------------
    # CITATION VALIDATION
    # --------------------------------------------------------

    @staticmethod
    def validate_citations(
        answer: str,
        sources: list[dict[str, Any]],
    ) -> dict[str, Any]:

        import re

        valid_labels = {
            source["label"]
            for source in sources
        }

        mentioned_labels = re.findall(
            r"\[(S\d+)\]",
            answer,
        )

        cited_sources = []
        invalid_labels = []

        for label in dict.fromkeys(mentioned_labels):

            if label in valid_labels:
                cited_sources.append(label)
            else:
                invalid_labels.append(label)

        # Remove invalid citation labels.
        for label in invalid_labels:
            answer = re.sub(
                rf"\[{re.escape(label)}\]",
                "",
                answer,
            )

        return {
            "answer": answer.strip(),
            "cited_sources": cited_sources,
            "invalid_source_labels": invalid_labels,
        }

    # --------------------------------------------------------
    # EVIDENCE STATUS
    # --------------------------------------------------------

    @staticmethod
    def determine_evidence_status(
        answer: str,
        cited_sources: list[str],
    ) -> str:

        answer_lower = answer.lower()

        is_insufficient = any(
            phrase in answer_lower
            for phrase in INSUFFICIENT_EVIDENCE_PHRASES
        )

        if is_insufficient:
            return "insufficient"

        if not cited_sources:
            return "uncited"

        return "retrieval_backed"

    # --------------------------------------------------------
    # MAIN QUESTION ANSWERING PIPELINE
    # --------------------------------------------------------

    def ask(self, question: str) -> dict[str, Any]:

        question = question.strip()

        if not question:
            raise ValueError("Question cannot be empty.")

        total_start = time.perf_counter()

        # STEP 1: Retrieve relevant passages.
        retrieval_start = time.perf_counter()

        retrieval_results = self.retriever.search(
            question,
            top_k=self.top_k,
        )

        retrieval_latency_ms = round(
            (time.perf_counter() - retrieval_start) * 1000,
            2,
        )

        print(
            f"\nRetrieved {len(retrieval_results)} passages."
        )

        # STEP 2: Build context.
        context, sources = self.build_context(
            retrieval_results
        )

        if not context or not sources:
            return {
                "question": question,
                "answer": (
                    "The available documents do not provide "
                    "sufficient evidence to answer this question."
                ),
                "sources": [],
                "cited_sources": [],
                "invalid_source_labels": [],
                "evidence_status": "insufficient",
                "retrieval": {},
                "generation": {},
                "total_latency_ms": round(
                    (time.perf_counter() - total_start) * 1000,
                    2,
                ),
            }

        # STEP 3: Build LLM prompt.
        user_prompt = build_user_prompt(
            question=question,
            context=context,
        )

        # STEP 4: Generate grounded answer.
        generation_result = self.llm.generate(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=user_prompt,
        )

        raw_answer = generation_result["answer"]

        # STEP 5: Validate citations.
        citation_result = self.validate_citations(
            answer=raw_answer,
            sources=sources,
        )

        answer = citation_result["answer"]

        cited_sources = citation_result["cited_sources"]

        # STEP 6: Determine evidence status.
        evidence_status = self.determine_evidence_status(
            answer=answer,
            cited_sources=cited_sources,
        )

        total_latency_ms = round(
            (time.perf_counter() - total_start) * 1000,
            2,
        )

        # STEP 7: Return structured response.
        return {
            "question": question,
            "answer": answer,

            # All passages retrieved by the retriever.
            "sources": sources,

            # Only citations actually referenced in the answer.
            "cited_sources": cited_sources,

            "invalid_source_labels": citation_result[
                "invalid_source_labels"
            ],

            "evidence_status": evidence_status,

            "retrieval": {
                "result_count": len(retrieval_results),
                "strategy": (
                    retrieval_results[0].get("retrieval_strategy")
                    if retrieval_results else None
                ),
                "latency_ms": retrieval_latency_ms,
            },

            "generation": {
                "model": generation_result["model"],
                "latency_ms": generation_result["latency_ms"],
                "prompt_tokens": generation_result["prompt_tokens"],
                "completion_tokens": generation_result[
                    "completion_tokens"
                ],
            },

            "total_latency_ms": total_latency_ms,

            "document_notice": (
                "Retrieved materials may include synthetic internal "
                "training drafts. Verify document approval and site "
                "applicability before operational use."
            ),
        }

    # --------------------------------------------------------
    # RESPONSE DISPLAY
    # --------------------------------------------------------

    @staticmethod
    def display_response(
        response: dict[str, Any],
    ) -> None:

        print("\n" + "=" * 65)
        print("SITESENSE GROUNDED QA RESPONSE")
        print("=" * 65)

        print("\nQUESTION:")
        print(response["question"])

        print("\nANSWER:")
        print(response["answer"])

        print("\nEVIDENCE STATUS:")
        print(response["evidence_status"].upper())

        cited_labels = set(
            response.get("cited_sources", [])
        )

        cited_sources = [
            source
            for source in response.get("sources", [])
            if source["label"] in cited_labels
        ]

        print("\nCITED SOURCES:")

        if cited_sources:

            for source in cited_sources:
                print(
                    f"\n[{source['label']}] "
                    f"{source['document_id']}"
                )

                print(
                    f"    Type: {source['document_type']}"
                )

                print(
                    f"    Page: {source['page_number']}"
                )

                print(
                    f"    Chunk: {source['chunk_id']}"
                )

        else:
            print("No valid sources were cited in the answer.")

        print("\nRETRIEVAL DETAILS:")

        retrieval = response.get("retrieval", {})

        print(
            f"Strategy: {retrieval.get('strategy', 'N/A')}"
        )

        print(
            f"Retrieved passages: "
            f"{retrieval.get('result_count', 0)}"
        )

        print(
            f"Retrieval latency: "
            f"{retrieval.get('latency_ms', 0)} ms"
        )

        print("\nGENERATION DETAILS:")

        generation = response.get("generation", {})

        print(
            f"Model: {generation.get('model', 'N/A')}"
        )

        print(
            f"Generation latency: "
            f"{generation.get('latency_ms', 0)} ms"
        )

        print(
            f"Prompt tokens: "
            f"{generation.get('prompt_tokens', 0)}"
        )

        print(
            f"Completion tokens: "
            f"{generation.get('completion_tokens', 0)}"
        )

        print(
            f"\nTotal latency: "
            f"{response.get('total_latency_ms', 0)} ms"
        )

        if response.get("invalid_source_labels"):
            print(
                "\nWARNING: Invalid citation labels detected: "
                f"{response['invalid_source_labels']}"
            )

        if response.get("document_notice"):
            print("\nDOCUMENT NOTICE:")
            print(response["document_notice"])

        print("\n" + "=" * 65)


# ============================================================
# INTERACTIVE APPLICATION
# ============================================================

def main():

    print("\n" + "=" * 65)
    print("SITESENSE - GROUNDED QUESTION ANSWERING")
    print("=" * 65)

    qa = GroundedQA(
        model=DEFAULT_MODEL,
        top_k=DEFAULT_TOP_K,
    )

    print("\nChecking Ollama connection...")

    if not qa.llm.check_connection():
        print(
            "\nOllama is unavailable or the configured model "
            "is missing."
        )
        print("Start Ollama and verify the model installation.")
        return

    print("Ollama connected successfully.")

    print("\nAsk questions about your warehouse documents.")
    print("Type 'exit' or 'quit' to close the application.")

    while True:

        try:
            question = input("\nEnter your question: ").strip()

            if question.lower() in {"exit", "quit"}:
                print("\nSITESENSE QA closed.")
                break

            if not question:
                print("Please enter a valid question.")
                continue

            print("\nProcessing your question...")

            response = qa.ask(question)

            qa.display_response(response)

        except KeyboardInterrupt:
            print("\n\nApplication interrupted.")
            break

        except Exception as error:
            print(f"\nERROR: {error}")
            print("Please check the retrieval and Ollama services.")


if __name__ == "__main__":
    main()
