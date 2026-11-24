
import json
import re
from pathlib import Path

from rank_bm25 import BM25Okapi
from nltk.stem import PorterStemmer


ROOT = Path(__file__).resolve().parents[2]

CHUNKS_FILE = ROOT / "data/extracted/chunks.json"
DATASET_FILE = ROOT / "genai/evaluation/retrieval_dataset.json"
OUTPUT_FILE = ROOT / "genai/evaluation/bm25_tokenizer_comparison.json"

TOP_K = 20

# Common English words. This is an experimental list,
# not a claim that every listed word is always irrelevant.
STOPWORDS = {
    "a", "an", "the", "and", "or", "but",
    "is", "are", "was", "were", "be", "been",
    "being", "do", "does", "did",
    "what", "which", "who", "whom",
    "how", "when", "where", "why",
    "should", "would", "could", "can",
    "may", "might", "must",
    "i", "we", "you", "they", "he", "she",
    "it", "them", "their", "our", "your",
    "this", "that", "these", "those",
    "to", "of", "in", "on", "at", "by",
    "for", "from", "with", "without",
    "as", "into", "through", "about",
    "after", "before", "during",
    "have", "has", "had",
    "will", "shall",
}


stemmer = PorterStemmer()


def baseline_tokenize(text):
    """Original production tokenizer."""
    return re.findall(r"[a-z0-9]+", text.lower())


def stopword_tokenize(text):
    """Lowercase tokenization with stopword filtering."""
    tokens = baseline_tokenize(text)

    return [
        token for token in tokens
        if token not in STOPWORDS
    ]


def stemmed_tokenize(text):
    """Stopword filtering followed by Porter stemming."""
    tokens = stopword_tokenize(text)

    return [
        stemmer.stem(token)
        for token in tokens
    ]


TOKENIZERS = {
    "baseline": baseline_tokenize,
    "stopword_filtered": stopword_tokenize,
    "stopword_stemmed": stemmed_tokenize,
}


def load_json(path):
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def calculate_recall(ranked_ids, relevant):
    relevant_ids = set(relevant)

    if not relevant_ids:
        return 0.0

    found = sum(
        1 for chunk_id in ranked_ids
        if chunk_id in relevant_ids
    )

    return found / len(relevant_ids)


def calculate_mrr(ranked_ids, relevant):
    relevant_ids = set(relevant)

    for rank, chunk_id in enumerate(ranked_ids, start=1):
        if chunk_id in relevant_ids:
            return 1.0 / rank

    return 0.0


def calculate_ndcg(ranked_ids, relevant, k):
    relevance = {
        chunk_id: grade
        for chunk_id, grade in relevant.items()
    }

    def dcg(grades):
        total = 0.0

        for rank, grade in enumerate(grades, start=1):
            gain = (2 ** grade) - 1
            total += gain / (
                __import__("math").log2(rank + 1)
            )

        return total

    actual_grades = [
        relevance.get(chunk_id, 0)
        for chunk_id in ranked_ids[:k]
    ]

    ideal_grades = sorted(
        relevance.values(),
        reverse=True
    )[:k]

    ideal_dcg = dcg(ideal_grades)

    if ideal_dcg == 0:
        return 0.0

    return dcg(actual_grades) / ideal_dcg


def evaluate_variant(chunks, queries, tokenizer):
    tokenized_corpus = [
        tokenizer(chunk["text"])
        for chunk in chunks
    ]

    model = BM25Okapi(tokenized_corpus)

    per_query = []

    for query_data in queries:
        question = query_data["query"]
        relevant = query_data["relevant_chunks"]

        query_tokens = tokenizer(question)

        if not query_tokens:
            raise ValueError(
                f"Query produced no tokens: {question}"
            )

        scores = model.get_scores(query_tokens)

        ranked_indices = sorted(
            range(len(scores)),
            key=lambda index: scores[index],
            reverse=True
        )

        ranked_ids = [
            chunks[index]["chunk_id"]
            for index in ranked_indices[:TOP_K]
        ]

        metrics = {
            "recall@5": calculate_recall(
                ranked_ids[:5], relevant
            ),
            "recall@10": calculate_recall(
                ranked_ids[:10], relevant
            ),
            "mrr": calculate_mrr(
                ranked_ids, relevant
            ),
            "ndcg@5": calculate_ndcg(
                ranked_ids, relevant, 5
            ),
            "ndcg@10": calculate_ndcg(
                ranked_ids, relevant, 10
            ),
        }

        per_query.append({
            "query_id": query_data["query_id"],
            "query": question,
            "metrics": metrics,
            "top_10": ranked_ids[:10],
        })

    metric_names = [
        "recall@5",
        "recall@10",
        "mrr",
        "ndcg@5",
        "ndcg@10",
    ]

    macro_average = {
        metric: sum(
            item["metrics"][metric]
            for item in per_query
        ) / len(per_query)
        for metric in metric_names
    }

    return {
        "macro_average": macro_average,
        "per_query": per_query,
    }


def main():
    print("\nLoading chunks and evaluation dataset...")

    chunk_data = load_json(CHUNKS_FILE)
    dataset = load_json(DATASET_FILE)

    chunks = chunk_data["chunks"]
    queries = dataset["queries"]

    if not chunks or not queries:
        raise ValueError("Chunks or evaluation queries are empty.")

    print(f"Chunks: {len(chunks)}")
    print(f"Evaluation queries: {len(queries)}")

    all_results = {
        "experiment": "BM25 tokenizer comparison",
        "chunk_count": len(chunks),
        "query_count": len(queries),
        "variants": {},
    }

    for name, tokenizer in TOKENIZERS.items():
        print("\n" + "=" * 75)
        print(f"Evaluating: {name}")
        print("=" * 75)

        result = evaluate_variant(
            chunks,
            queries,
            tokenizer
        )

        all_results["variants"][name] = result

        for metric, value in result["macro_average"].items():
            print(f"{metric:<15}: {value:.4f}")

    print("\n" + "=" * 75)
    print("TOKENIZER COMPARISON")
    print("=" * 75)

    metric_names = [
        "recall@5",
        "recall@10",
        "mrr",
        "ndcg@5",
        "ndcg@10",
    ]

    print(
        f"{'METRIC':<15}"
        f"{'BASELINE':<15}"
        f"{'STOPWORDS':<15}"
        f"{'STOP + STEM':<15}"
    )

    for metric in metric_names:
        values = [
            all_results["variants"][variant]["macro_average"][metric]
            for variant in TOKENIZERS
        ]

        print(
            f"{metric:<15}"
            f"{values[0]:<15.4f}"
            f"{values[1]:<15.4f}"
            f"{values[2]:<15.4f}"
        )

    with open(OUTPUT_FILE, "w", encoding="utf-8") as file:
        json.dump(
            all_results,
            file,
            indent=4,
            ensure_ascii=False
        )

    print("\nResults saved to:")
    print(OUTPUT_FILE)

    print("\nBM25 TOKENIZER EXPERIMENT COMPLETED")


if __name__ == "__main__":
    main()
