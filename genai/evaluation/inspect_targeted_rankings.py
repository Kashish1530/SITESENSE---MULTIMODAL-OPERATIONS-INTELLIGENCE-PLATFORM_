
import json
from pathlib import Path

from genai.evaluation.evaluate_retrieval import load_dataset


PROJECT_ROOT = Path(__file__).resolve().parents[2]

RESULTS_FILE = (
    PROJECT_ROOT
    / "genai"
    / "evaluation"
    / "targeted_multi_query_evaluation_results.json"
)


def print_ranking(title, chunk_ids, relevant_chunks):

    print(f"\n{title}")
    print("-" * 90)
    print(f"{'Rank':<8}{'Chunk ID':<28}{'Grade':<10}{'Relevance'}")
    print("-" * 90)

    for rank, chunk_id in enumerate(chunk_ids, start=1):

        grade = relevant_chunks.get(chunk_id, 0)

        if grade == 3:
            relevance = "Highly relevant"
        elif grade == 2:
            relevance = "Relevant"
        elif grade == 1:
            relevance = "Supporting"
        else:
            relevance = "Not labelled / irrelevant"

        print(
            f"{rank:<8}{chunk_id:<28}{grade:<10}{relevance}"
        )


def print_relevant_positions(title, chunk_ids, relevant_chunks):

    positions = {
        chunk_id: rank
        for rank, chunk_id in enumerate(chunk_ids, start=1)
    }

    print(f"\n{title} — relevant chunk positions")
    print("-" * 75)

    for chunk_id, grade in sorted(
        relevant_chunks.items(),
        key=lambda item: (-item[1], item[0])
    ):

        position = positions.get(chunk_id)

        if position is None:
            position_text = "NOT RETRIEVED"
        else:
            position_text = f"Rank {position}"

        print(
            f"{chunk_id:<28} Grade: {grade}    {position_text}"
        )


def main():

    with open(RESULTS_FILE, "r", encoding="utf-8") as file:
        results = json.load(file)

    dataset = load_dataset()

    dataset_queries = {
        item["query_id"]: item
        for item in dataset["queries"]
    }

    print("\nSITESENSE TARGETED RETRIEVAL RANKING AUDIT")
    print("=" * 90)

    for query_id in results["target_query_ids"]:

        print("\n" + "#" * 90)
        print(f"QUERY: {query_id}")
        print("#" * 90)

        query_results = results["queries"][query_id]

        relevant_chunks = dataset_queries[query_id]["relevant_chunks"]

        baseline = query_results["baseline"]
        multi_query = query_results["multi_query"]

        print("\nOriginal question:")
        print(query_results["original_query"])

        print_ranking(
            "BASELINE — HYBRID + RERANKER",
            baseline["reranked_chunk_ids"],
            relevant_chunks,
        )

        print_ranking(
            "TARGETED MULTI-QUERY — RRF",
            multi_query["rrf_chunk_ids"],
            relevant_chunks,
        )

        print_ranking(
            "TARGETED MULTI-QUERY — RRF + RERANKER",
            multi_query["reranked_chunk_ids"],
            relevant_chunks,
        )

        print_relevant_positions(
            "BASELINE",
            baseline["reranked_chunk_ids"],
            relevant_chunks,
        )

        print_relevant_positions(
            "TARGETED MULTI-QUERY + RERANKER",
            multi_query["reranked_chunk_ids"],
            relevant_chunks,
        )


if __name__ == "__main__":
    main()

