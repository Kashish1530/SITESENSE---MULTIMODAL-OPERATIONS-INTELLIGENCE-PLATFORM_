
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FILE = ROOT / "genai" / "evaluation" / "unlabelled_candidates.json"

TARGETS = {"Q001", "Q002", "Q003", "Q004"}

def main():
    with open(FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    output_dir = ROOT / "genai" / "evaluation" / "candidate_reports"
    output_dir.mkdir(parents=True, exist_ok=True)

    for item in data:
        query_id = item["query_id"]

        if query_id not in TARGETS:
            continue

        lines = [
            "=" * 80,
            f"{query_id} - {item['query']}",
            "=" * 80,
            f"Total candidates: {len(item['candidates'])}",
            ""
        ]

        for candidate in item["candidates"]:
            lines.extend([
                "-" * 80,
                f"Chunk: {candidate['chunk_id']}",
                f"Semantic rank: {candidate['dense_rank']}",
                f"BM25 rank: {candidate['bm25_rank']}",
                "Content:",
                candidate["text"],
                ""
            ])

        report = "\n".join(lines)
        report_path = output_dir / f"{query_id}_candidates.txt"
        report_path.write_text(report, encoding="utf-8")

        print(f"{query_id}: saved {len(item['candidates'])} candidates")
        print(f"File: {report_path}")

if __name__ == "__main__":
    main()
