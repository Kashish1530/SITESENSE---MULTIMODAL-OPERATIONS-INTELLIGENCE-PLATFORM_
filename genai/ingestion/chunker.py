
import json
import re
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_FILE = PROJECT_ROOT / "data" / "extracted" / "documents.json"

OUTPUT_DIR = PROJECT_ROOT / "data" / "extracted"

OUTPUT_FILE = OUTPUT_DIR / "chunks.json"


# Chunking configuration
CHUNK_SIZE = 800
CHUNK_OVERLAP = 120


def normalize_text(text: str) -> str:
    """
    Normalize whitespace introduced during PDF extraction.

    Joins wrapped lines without removing meaningful punctuation
    or bullet markers.
    """

    if not text:
        return ""

    # Replace newlines, tabs and repeated whitespace with one space.
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def split_into_sentences(text: str) -> list:
    """
    Split text at sentence-ending punctuation.

    Sentence boundaries are preferred over arbitrary character
    positions.

    Headings without punctuation remain attached to their
    following content.
    """

    if not text:
        return []

    # Split after ., ! or ? when followed by whitespace.
    sentences = re.split(
        r"(?<=[.!?])\s+",
        text
    )

    return [
        sentence.strip()
        for sentence in sentences
        if sentence.strip()
    ]


def split_long_sentence(sentence: str) -> list:
    """
    Handle an unusually long sentence that exceeds CHUNK_SIZE.

    Prefer word boundaries instead of cutting through words.
    """

    if len(sentence) <= CHUNK_SIZE:
        return [sentence]

    words = sentence.split()

    fragments = []
    current_words = []

    for word in words:

        candidate = " ".join(current_words + [word])

        if len(candidate) <= CHUNK_SIZE:
            current_words.append(word)

        else:

            if current_words:
                fragments.append(" ".join(current_words))

            current_words = [word]

    if current_words:
        fragments.append(" ".join(current_words))

    return fragments


def prepare_units(text: str) -> list:
    """
    Convert page text into sentence-level units.

    Oversized sentences are split at word boundaries.
    """

    normalized_text = normalize_text(text)

    if not normalized_text:
        return []

    sentences = split_into_sentences(normalized_text)

    units = []

    for sentence in sentences:

        fragments = split_long_sentence(sentence)

        units.extend(fragments)

    return units


def build_chunks(units: list) -> list:
    """
    Build chunks using sentence-level overlap.

    Each chunk targets CHUNK_SIZE characters.

    Consecutive chunks share complete trailing sentence units
    up to approximately CHUNK_OVERLAP characters.
    """

    if not units:
        return []

    chunks = []

    start = 0
    total_units = len(units)

    while start < total_units:

        current_units = []
        current_length = 0

        end = start

        # Add complete units while respecting the target size.
        while end < total_units:

            unit = units[end]

            separator_length = 1 if current_units else 0

            new_length = (
                current_length
                + separator_length
                + len(unit)
            )

            if new_length > CHUNK_SIZE and current_units:
                break

            current_units.append(unit)
            current_length = new_length

            end += 1

            # An individual oversized word is kept intact.
            # Normally, oversized sentences have already been split.
            if current_length >= CHUNK_SIZE:
                break

        chunk_text = " ".join(current_units).strip()

        if chunk_text:
            chunks.append(chunk_text)

        if end >= total_units:
            break

        # Calculate sentence-level overlap for the next chunk.
        overlap_length = 0
        next_start = end

        for index in range(end - 1, start - 1, -1):

            unit_length = len(units[index])

            separator_length = 1 if overlap_length > 0 else 0

            proposed_length = (
                overlap_length
                + separator_length
                + unit_length
            )

            if proposed_length > CHUNK_OVERLAP:
                # Keep at least the most recent complete unit
                # when it is larger than the overlap target.
                if overlap_length == 0:
                    next_start = index

                break

            overlap_length = proposed_length
            next_start = index

        # Guarantee forward progress.
        if next_start <= start:
            next_start = end

        start = next_start

    return chunks


def split_text(text: str) -> list:
    """
    Main chunking function.

    Pipeline:
    1. Normalize extracted text.
    2. Split into sentences.
    3. Handle oversized sentences.
    4. Build chunks with sentence-level overlap.
    """

    units = prepare_units(text)

    return build_chunks(units)


def create_document_chunks(document: dict) -> list:
    """
    Generate chunks for every page of a document.

    Preserves source metadata and page-level traceability.
    """

    document_chunks = []

    document_id = document["document_id"]

    for page in document["pages"]:

        page_text = page["text"]

        page_number = page["page_number"]

        page_chunks = split_text(page_text)

        for chunk_index, chunk_text in enumerate(
            page_chunks,
            start=1
        ):

            chunk_id = (
                f"{document_id}-"
                f"P{page_number:02d}-"
                f"C{chunk_index:02d}"
            )

            document_chunks.append({

                "chunk_id": chunk_id,

                "document_id": document_id,

                "document_type": document["document_type"],

                "source_file": document["source_file"],

                "page_number": page_number,

                "chunk_index": chunk_index,

                "text": chunk_text,

                "character_count": len(chunk_text),

            })

    return document_chunks


def validate_chunks(chunks: list) -> None:
    """
    Validate generated chunk records.
    """

    chunk_ids = [
        chunk["chunk_id"]
        for chunk in chunks
    ]

    if len(chunk_ids) != len(set(chunk_ids)):
        raise ValueError("Duplicate chunk IDs detected.")

    for chunk in chunks:

        if not chunk["text"].strip():
            raise ValueError(
                f"Empty chunk detected: {chunk['chunk_id']}"
            )

        if chunk["character_count"] != len(chunk["text"]):
            raise ValueError(
                f"Character count mismatch: {chunk['chunk_id']}"
            )

    print("Chunk validation passed.")


def run_chunking():

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Extraction file not found: {INPUT_FILE}"
        )

    with INPUT_FILE.open("r", encoding="utf-8") as file:
        data = json.load(file)

    all_chunks = []

    for document in data["documents"]:

        document_chunks = create_document_chunks(document)

        all_chunks.extend(document_chunks)

        print(
            f"{document['document_id']}: "
            f"{len(document_chunks)} chunks"
        )

    validate_chunks(all_chunks)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    output_data = {

        "dataset": data["dataset"],

        "chunk_size": CHUNK_SIZE,

        "chunk_overlap": CHUNK_OVERLAP,

        "chunking_strategy": "sentence_aware",

        "total_documents": len(data["documents"]),

        "total_chunks": len(all_chunks),

        "chunks": all_chunks,

    }

    with OUTPUT_FILE.open("w", encoding="utf-8") as file:

        json.dump(
            output_data,
            file,
            indent=4,
            ensure_ascii=False
        )

    print("\n" + "=" * 50)

    print("CHUNKING SUMMARY")

    print("=" * 50)

    print(f"Documents processed : {len(data['documents'])}")

    print(f"Total chunks        : {len(all_chunks)}")

    print(f"Chunk size          : {CHUNK_SIZE}")

    print(f"Chunk overlap       : {CHUNK_OVERLAP}")

    print("Strategy            : Sentence-aware")

    print(f"Output file         : {OUTPUT_FILE}")


if __name__ == "__main__":
    run_chunking()
