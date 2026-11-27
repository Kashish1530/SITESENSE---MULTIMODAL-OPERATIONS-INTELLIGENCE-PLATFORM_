
from pathlib import Path
import re


# Project root: SITESENSE/
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Source directories
POLICY_DIR = PROJECT_ROOT / "data" / "policies"
HANDBOOK_DIR = PROJECT_ROOT / "data" / "handbooks"


def load_pdf_files():
    """
    Discover all PDF files from the policies and handbooks folders.

    Returns:
        list[dict]: PDF paths and their document categories.
    """

    documents = []

    source_directories = [
        (POLICY_DIR, "policy"),
        (HANDBOOK_DIR, "handbook"),
    ]

    for directory, document_type in source_directories:

        if not directory.exists():
            print(f"Warning: Directory not found: {directory}")
            continue

        pdf_files = sorted(directory.glob("*.pdf"))

        for pdf_path in pdf_files:

            documents.append({
                "file_path": pdf_path,
                "document_type": document_type,
            })

    return documents


def extract_document_id(filename):
    """
    Extract the document ID from the filename.

    Examples:
        WHP-001_Warehouse_Policy.pdf -> WHP-001
        SHB-01_Safety_Handbook.pdf -> SHB-01
    """

    match = re.match(r"^(WHP-\d{3}|SHB-\d{2})", filename)

    if match:
        return match.group(1)

    return None
