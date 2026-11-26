# harsh changes starts
from functools import lru_cache
from pathlib import Path
from datetime import date
from uuid import uuid4
import re

from sqlalchemy.orm import Session

from app.config.settings import get_settings
settings = get_settings()  # harsh changes
from app.models.knowledge_compliance import Policy, PolicyChunk
from app.models.users_sites import Site
from app.api.deps import verify_site_access

from genai.ingestion.text_extractor import extract_pdf_text
from genai.ingestion.chunker import create_document_chunks, validate_chunks
from genai.embeddings.embedding_services import (
    load_embedding_model,
    generate_embeddings,
    build_embedding_records,
)


@lru_cache(maxsize=1)
def get_embedding_model():
    """Load the embedding model once and reuse it."""
    return load_embedding_model()


class PolicyIngestionService:

    @staticmethod
    def ingest(
        db: Session,
        site_id,
        current_user,
        upload,
        title: str,
        version: str = "1.0",
        effective_date: date | None = None,
        description: str | None = None,
    ):
        saved_path = None

        try:
            # Verify that the target site exists and the user can access it.
            site = db.query(Site).filter(Site.id == site_id).first()
            if not site:
                raise ValueError("Selected site does not exist.")

            verify_site_access(site_id, current_user, db)

            original_name = Path(upload.filename or "policy.pdf").name
            if Path(original_name).suffix.lower() != ".pdf":
                raise ValueError("Only PDF policy documents are supported.")

            # Save under a site-specific directory. Never trust the supplied filename.
            safe_name = re.sub(r"[^A-Za-z0-9._-]", "_", original_name)
            storage_root = (
                Path(settings.MEDIA_STORAGE_PATH).resolve()
                / "policies"
                / str(site_id)
            )
            storage_root.mkdir(parents=True, exist_ok=True)

            stored_name = f"{uuid4().hex}_{safe_name}"
            saved_path = storage_root / stored_name

            max_bytes = int(settings.MAX_UPLOAD_SIZE_MB) * 1024 * 1024
            total_bytes = 0

            with saved_path.open("wb") as destination:
                while True:
                    block = upload.file.read(1024 * 1024)
                    if not block:
                        break

                    total_bytes += len(block)
                    if total_bytes > max_bytes:
                        raise ValueError(
                            f"File exceeds the {settings.MAX_UPLOAD_SIZE_MB} MB limit."
                        )

                    destination.write(block)

            if total_bytes == 0:
                raise ValueError("The uploaded file is empty.")

            # Confirm that the uploaded content is actually a PDF.
            with saved_path.open("rb") as source:
                if source.read(5) != b"%PDF-":
                    raise ValueError("The uploaded file is not a valid PDF.")

            # Extract page-level text using the existing project extractor.
            pages = extract_pdf_text(saved_path)
            if not pages or not any(page.get("has_text") for page in pages):
                raise ValueError(
                    "No readable text was found. Scanned PDFs need OCR support."
                )

            policy_id = uuid4()

            document = {
                "document_id": str(policy_id),
                "document_type": "policy",
                "source_file": original_name,
                "pages": pages,
            }

            chunks = create_document_chunks(document)
            if not chunks:
                raise ValueError("No text chunks could be generated.")

            validate_chunks(chunks)

            model = get_embedding_model()
            vectors = generate_embeddings(model, chunks)
            records = build_embedding_records(chunks, vectors)

            relative_path = str(
                Path("policies") / str(site_id) / stored_name
            ).replace("\\", "/")

            policy = Policy(
                id=policy_id,
                site_id=site_id,
                title=title.strip(),
                version=version.strip(),
                source_file=original_name,
                effective_date=effective_date,
                file_path=relative_path,
                description=description,
                status="active",
            )

            db.add(policy)
            db.flush()

            policy_chunks = []
            for chunk, record in zip(chunks, records):
                policy_chunks.append(
                    PolicyChunk(
                        policy_id=policy_id,
                        chunk_index=chunk["chunk_index"],
                        content=chunk["text"],
                        page_number=chunk["page_number"],
                        embedding=record["embedding"],
                        embedding_id=chunk["chunk_id"],
                        metadata_json={
                            "document_id": str(policy_id),
                            "document_type": "policy",
                            "source_file": original_name,
                            "character_count": chunk["character_count"],
                        },
                    )
                )

            db.add_all(policy_chunks)
            db.commit()

            return {
                "policy_id": str(policy_id),
                "site_id": str(site_id),
                "title": title,
                "filename": original_name,
                "pages_extracted": len(pages),
                "chunks_created": len(policy_chunks),
                "embedding_dimension": 384,
                "status": "active",
                "message": "Policy uploaded and indexed successfully.",
            }

        except Exception:
            db.rollback()
            if saved_path and saved_path.exists():
                saved_path.unlink(missing_ok=True)
            raise

        finally:
            upload.file.close()
# harsh changes end