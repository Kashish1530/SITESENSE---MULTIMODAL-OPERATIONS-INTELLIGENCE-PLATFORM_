
import json
from pathlib import Path

from sentence_transformers import CrossEncoder

from genai.retrieval.pgvector_search import semantic_search
from genai.retrieval.bm25_search import BM25Search
from genai.retrieval.hybrid_search import reciprocal_rank_fusion

from genai.evaluation.evaluate_retrieval import (
    load_dataset,
    calculate_metrics,
)


# ==========================================================
# CONFIGURATION
# ==========================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

OUTPUT_FILE = (
    PROJECT_ROOT
    / "genai"
    / "evaluation"
    / "reranker_model_comparison_results.json"
)

MODELS = [
    "cross-encoder/ms-marco-MiniLM-L-6-v2",
    "cross-encoder/ms-marco-MiniLM-L-12-v2",
    "BAAI/bge-reranker-base",
]

RETRIEVAL_TOP_K = 20
FINAL_TOP_K = 20
RRF_K = 60


# ==========================================================
# DOCUMENT FORMATTING
# Keep this identical to the existing production reranker.
# ==========================================================

def prepare_document(document):

    document_id = document.get("document_id", "Unknown")

    source_file = document.get("source_file", "Unknown")

    page_number = document.get("page_number", "Unknown")

    source_title = Path(source_file).stem.replace("_", " ")

    content = document.get("text", "")

    return (
        f"Document ID: {document_id}\n"
        f"Document title: {source_title}\n"
        f"Page number: {page_number}\n"
        f"Document content:\n{content}"
    )


# ==========================================================
# PREPARE CANDIDATES
# Retrieval happens only once per query.
# Every reranker receives the exact same candidates.
# ==========================================================

def prepare_candidates(dataset):

    print("\nInitializing BM25...")
    bm25_engine = BM25Search()

    candidate_sets = []

    for index, item in enumerate(dataset["queries"], start=1):

        query_id = item["query_id"]
        query = item["query"]

        print(
            f"\nPreparing candidates "
            f"{index}/{len(dataset['queries'])}: {query_id}"
        )

        dense_results = semantic_search(
            query=query,
            top_k=RETRIEVAL_TOP_K,
        )

        bm25_results = bm25_engine.search(
            query=query,
            top_k=RETRIEVAL_TOP_K,
        )

        hybrid_results = reciprocal_rank_fusion(
            ranked_lists=[
                ("dense", dense_results),
                ("bm25", bm25_results),
            ],
            top_k=RETRIEVAL_TOP_K,
            rrf_k=RRF_K,
        )

        candidate_sets.append({
            "query_id": query_id,
            "query": query,
            "relevant_chunks": item["relevant_chunks"],
            "candidates": hybrid_results,
        })

        print(
            f"Candidates prepared: {len(hybrid_results)}"
        )

    return candidate_sets


# ==========================================================
# EVALUATE ONE MODEL
# ==========================================================

def evaluate_model(model_name, candidate_sets):

    print("\n" + "=" * 100)
    print(f"MODEL: {model_name}")
    print("=" * 100)

    print("\nLoading model...")

    model = CrossEncoder(
        model_name,
        max_length=512,
    )

    query_results = []

    for item in candidate_sets:

        query_id = item["query_id"]
        query = item["query"]
        relevant_chunks = item["relevant_chunks"]
        candidates = item["candidates"]

        print(f"\nEvaluating {query_id}: {query}")

        pairs = [
            (query, prepare_document(document))
            for document in candidates
        ]

        scores = model.predict(
            pairs,
            batch_size=8,
            show_progress_bar=False,
        )

        ranked_documents = []

        for document, score in zip(candidates, scores):

            result = document.copy()
            result["rerank_score"] = float(score)

            ranked_documents.append(result)

        ranked_documents.sort(
            key=lambda result: result["rerank_score"],
            reverse=True,
        )

        ranked_documents = ranked_documents[:FINAL_TOP_K]

        metrics = calculate_metrics(
            ranked_documents,
            relevant_chunks,
        )

        print(
            f"Recall@5: {metrics['Recall@5']:.4f} | "
            f"Recall@10: {metrics['Recall@10']:.4f} | "
            f"MRR: {metrics['MRR']:.4f} | "
            f"nDCG@5: {metrics['nDCG@5']:.4f} | "
            f"nDCG@10: {metrics['nDCG@10']:.4f}"
        )

        print("Top 5:")

        for rank, document in enumerate(
            ranked_documents[:5],
            start=1,
        ):

            print(
                f"  {rank}. {document['chunk_id']} "
                f"| Score: {document['rerank_score']:.4f}"
            )

        query_results.append({
            "query_id": query_id,
            "metrics": metrics,
            "ranked_chunk_ids": [
                document["chunk_id"]
                for document in ranked_documents
            ],
        })

    # Calculate macro averages across all queries.
    metric_names = [
        "Recall@5",
        "Recall@10",
        "MRR",
        "nDCG@5",
        "nDCG@10",
    ]

    macro_average = {}

    for metric in metric_names:

        values = [
            result["metrics"][metric]
            for result in query_results
        ]

        macro_average[metric] = round(
            sum(values) / len(values),
            4,
        )

    print("\nMACRO-AVERAGE RESULTS")
    print("-" * 60)

    for metric, value in macro_average.items():

        print(f"{metric:<15}: {value:.4f}")

    del model

    return {
        "model": model_name,
        "macro_average": macro_average,
        "queries": query_results,
    }


# ==========================================================
# MAIN
# ==========================================================

def main():

    print("\n" + "=" * 100)
    print(" SITESENSE - FULL RERANKER MODEL BENCHMARK")
    print("=" * 100)

    dataset = load_dataset()

    print("\nDataset:", dataset["dataset_name"])
    print("Total queries:", len(dataset["queries"]))

    # Prepare a fixed candidate set for every model.
    candidate_sets = prepare_candidates(dataset)

    all_model_results = []

    for model_name in MODELS:

        result = evaluate_model(
            model_name,
            candidate_sets,
        )

        all_model_results.append(result)

    # Save comparison results separately.
    output = {
        "benchmark": "SITESENSE Reranker Model Comparison",
        "total_queries": len(dataset["queries"]),
        "retrieval_top_k": RETRIEVAL_TOP_K,
        "final_top_k": FINAL_TOP_K,
        "rrf_k": RRF_K,
        "models": all_model_results,
    }

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            output,
            file,
            indent=4,
            ensure_ascii=False,
        )

    # Final comparison table.
    print("\n\n")
    print("=" * 100)
    print("FINAL MODEL COMPARISON")
    print("=" * 100)

    print(
        f"{'Model':<45}"
        f"{'R@5':>9}"
        f"{'R@10':>9}"
        f"{'MRR':>9}"
        f"{'nDCG@5':>10}"
        f"{'nDCG@10':>11}"
    )

    print("-" * 100)

    for result in all_model_results:

        metrics = result["macro_average"]

        print(
            f"{result['model']:<45}"
            f"{metrics['Recall@5']:>9.4f}"
            f"{metrics['Recall@10']:>9.4f}"
            f"{metrics['MRR']:>9.4f}"
            f"{metrics['nDCG@5']:>10.4f}"
            f"{metrics['nDCG@10']:>11.4f}"
        )

    print("\nBENCHMARK COMPLETED")

    print("\nResults saved to:")
    print(OUTPUT_FILE)


if __name__ == "__main__":
    main()
