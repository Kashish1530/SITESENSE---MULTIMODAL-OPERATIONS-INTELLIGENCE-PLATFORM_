
import json
from datetime import datetime, timezone
from pathlib import Path

from pypdf import PdfReader

from genai.ingestion.pdf_loader import (
    load_pdf_files,
    extract_document_id,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = PROJECT_ROOT / "data" / "extracted"
OUTPUT_FILE = OUTPUT_DIR / "documents.json"


def extract_pdf_text(pdf_path):
    """
    Extract text from a PDF page by page.

    Page numbers are stored as one-based numbers,
    matching the numbers users see in PDF readers.
    """

    reader = PdfReader(str(pdf_path), strict=False)

    extracted_pages = []

    for page_index, page in enumerate(reader.pages):

        page_number = page_index + 1

        text = page.extract_text() or ""

        extracted_pages.append({
            "page_number": page_number,
            "text": text.strip(),
            "has_text": bool(text.strip()),
        })

    return extracted_pages


def run_ingestion():

    documents = load_pdf_files()

    extracted_documents = []

    total_pages = 0
    empty_pages = 0
    failed_documents = []

    print(f"\nFound {len(documents)} PDF documents.")
    print("-" * 50)

    for document in documents:

        pdf_path = document["file_path"]
        document_type = document["document_type"]

        try:

            document_id = extract_document_id(pdf_path.name)

            if not document_id:
                print(f"Skipping invalid document ID: {pdf_path.name}")
                continue

            pages = extract_pdf_text(pdf_path)

            total_pages += len(pages)

            for page in pages:
                if not page["has_text"]:
                    empty_pages += 1

            extracted_documents.append({
                "document_id": document_id,
                "document_type": document_type,
                "source_file": pdf_path.name,
                "page_count": len(pages),
                "pages": pages,
            })

            print(
                f"Processed: {document_id} | "
                f"{len(pages)} pages"
            )

        except Exception as error:

            failed_documents.append({
                "source_file": pdf_path.name,
                "error": str(error),
            })

            print(f"Failed: {pdf_path.name} | {error}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    output_data = {
        "dataset": "ABC Company Warehouse",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_documents": len(extracted_documents),
        "total_pages": total_pages,
        "empty_pages": empty_pages,
        "failed_documents": failed_documents,
        "documents": extracted_documents,
    }

    with OUTPUT_FILE.open("w", encoding="utf-8") as file:
        json.dump(
            output_data,
            file,
            indent=4,
            ensure_ascii=False,
        )

    print("\n" + "=" * 50)
    print("INGESTION SUMMARY")
    print("=" * 50)

    print(f"Documents processed : {len(extracted_documents)}")
    print(f"Pages extracted    : {total_pages}")
    print(f"Pages without text : {empty_pages}")
    print(f"Failed documents   : {len(failed_documents)}")
    print(f"Output file        : {OUTPUT_FILE}")


if __name__ == "__main__":
    run_ingestion()
