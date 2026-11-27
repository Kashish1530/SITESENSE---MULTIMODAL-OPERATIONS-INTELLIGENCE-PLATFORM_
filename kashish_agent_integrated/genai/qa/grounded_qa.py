"""
SITESENSE - Grounded Policy QA Engine (Feature 3.2)
Performs hybrid retrieval against warehouse policies and safety handbooks,
formats context with exact page citations, and uses Groq LLM to synthesize
strictly grounded answers with refusal on non-matching queries.
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv
from groq import Groq

# Load environment
load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

from genai.retrieval.hybrid_search import HybridSearch
from genai.qa.prompt_templates import (
    GROUNDED_QA_SYSTEM_PROMPT,
    GROUNDED_QA_USER_TEMPLATE,
    NO_MATCH_REFUSAL_MESSAGE,
)


class GroundedPolicyQA:
    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
        self.api_key = os.getenv("GROQ_API_KEY")
        self.hybrid_engine = HybridSearch()
        self.min_rerank_threshold = -4.0

    def format_context(self, chunks: List[Dict[str, Any]]) -> str:
        formatted = []
        for i, chunk in enumerate(chunks, 1):
            chunk_id = chunk.get("chunk_id", "UNKNOWN")
            doc_id = chunk.get("document_id", "UNKNOWN")
            source = chunk.get("source_file", "")
            page = chunk.get("page_number", "1")
            text = chunk.get("text") or chunk.get("content", "")
            rerank_score = chunk.get("rerank_score", 0.0)

            header = f"--- Chunk {i} [{doc_id}, Page {page}, {chunk_id}] (Source: {source}, Relevance: {rerank_score:.2f}) ---"
            formatted.append(f"{header}\n{text}\n")
        return "\n".join(formatted)

    def answer_question(self, query: str, top_k: int = 5) -> Dict[str, Any]:
        """
        Executes hybrid retrieval, validates relevance threshold, and synthesizes grounded answer.
        """
        # Step 1: Hybrid retrieval (BM25 + Dense + RRF + Cross-Encoder)
        try:
            candidates = self.hybrid_engine.search(query, top_k=top_k)
        except Exception as e:
            return {
                "query": query,
                "found": False,
                "answer": f"Retrieval error: {e}",
                "citations": [],
                "chunks": []
            }

        # Step 2: Gating on relevance score
        valid_chunks = [c for c in candidates if c.get("rerank_score", -999.0) >= self.min_rerank_threshold]

        if not valid_chunks:
            return {
                "query": query,
                "found": False,
                "answer": NO_MATCH_REFUSAL_MESSAGE,
                "citations": [],
                "chunks": []
            }

        # Step 3: Format context & build citations list
        context_str = self.format_context(valid_chunks)
        citations = [
            {
                "chunk_id": c.get("chunk_id"),
                "document_id": c.get("document_id"),
                "source_file": c.get("source_file"),
                "page_number": c.get("page_number"),
                "rerank_score": round(float(c.get("rerank_score", 0.0)), 3)
            }
            for c in valid_chunks
        ]

        # Step 4: Synthesize grounded response using Groq
        if not self.api_key:
            return {
                "query": query,
                "found": True,
                "answer": f"Context retrieved successfully ({len(valid_chunks)} chunks), but GROQ_API_KEY is not configured for LLM synthesis.\n\nContext excerpt:\n{context_str[:500]}...",
                "citations": citations,
                "chunks": valid_chunks
            }

        try:
            client = Groq(api_key=self.api_key)
            prompt = GROUNDED_QA_USER_TEMPLATE.format(context=context_str, question=query)

            completion = client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": GROUNDED_QA_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=1024
            )
            answer_text = completion.choices[0].message.content
        except Exception as e:
            answer_text = f"LLM generation failed: {e}. Top cited chunk: [{citations[0]['document_id']}, Page {citations[0]['page_number']}]."

        return {
            "query": query,
            "found": True,
            "answer": answer_text,
            "citations": citations,
            "chunks": valid_chunks
        }


def answer_policy_question(query: str, top_k: int = 5) -> Dict[str, Any]:
    qa = GroundedPolicyQA()
    return qa.answer_question(query, top_k=top_k)
