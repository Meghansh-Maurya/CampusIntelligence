
from __future__ import annotations

import logging
import re
import uuid
from pathlib import Path

import pymupdf as fitz
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import Document, DocumentChunk
from app.services.ai_service import ai_is_configured, embed_texts

logger = logging.getLogger(__name__)

EMBEDDING_BATCH_SIZE = 32


def split_text(
    text: str,
    chunk_size: int = 1200,
    overlap: int = 180,
) -> list[str]:
    """Small, dependency-free overlapping chunker used by the RAG baseline."""
    clean = re.sub(r"\s+", " ", text).strip()

    if not clean:
        return []

    if chunk_size <= 0 or overlap < 0 or overlap >= chunk_size:
        raise ValueError(
            "chunk_size must be positive and overlap must be smaller than chunk_size."
        )

    chunks: list[str] = []
    start = 0

    while start < len(clean):
        end = min(start + chunk_size, len(clean))

        if end < len(clean):
            boundary = clean.rfind(
                " ",
                start + int(chunk_size * 0.65),
                end,
            )

            if boundary > start:
                end = boundary

        piece = clean[start:end].strip()

        if piece:
            chunks.append(piece)

        if end >= len(clean):
            break

        start = max(end - overlap, start + 1)

    return chunks


def extract_pdf_pages(file_path: Path) -> list[tuple[int, str]]:
    """Extract (one-based page number, text) from a PDF; scanned PDFs need OCR."""
    try:
        with fitz.open(file_path) as pdf:
            if len(pdf) > settings.max_pdf_pages:
                raise ValueError(
                    f"PDF exceeds the configured limit of "
                    f"{settings.max_pdf_pages} pages."
                )

            if pdf.is_encrypted:
                raise ValueError(
                    "Password-protected PDFs are not supported."
                )

            pages = [
                (index + 1, page.get_text("text").strip())
                for index, page in enumerate(pdf)
            ]

    except ValueError:
        raise

    except Exception as exc:
        raise ValueError(
            "This file could not be read as a valid PDF."
        ) from exc

    if not pages or not any(text for _, text in pages):
        raise ValueError(
            "No selectable text was found. Scanned PDFs need an OCR feature, "
            "which is not included in this version."
        )

    return pages


def make_page_chunks(
    pages: list[tuple[int, str]],
) -> list[tuple[int, int, str]]:
    result: list[tuple[int, int, str]] = []
    chunk_index = 0

    for page_number, page_text in pages:
        for part in split_text(page_text):
            result.append(
                (chunk_index, page_number, part)
            )
            chunk_index += 1

    return result


def save_document_file(contents: bytes) -> tuple[str, Path]:
    settings.storage_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    stored_filename = f"{uuid.uuid4().hex}.pdf"
    path = settings.storage_dir / stored_filename

    path.write_bytes(contents)

    return stored_filename, path


def index_document_chunks(
    db: Session,
    document: Document,
    chunks: list[tuple[int, int, str]],
) -> None:
    """
    Index document chunks.

    If Gemini embedding generation fails for a batch, the corresponding
    chunks are still saved with embedding=None. Other batches continue.
    """
    if not chunks:
        logger.info(
            "Document %s contains no chunks to index.",
            document.id,
        )
        return

    vectors: list[list[float] | None] = [None] * len(chunks)

    if ai_is_configured():
        total_batches = (
            len(chunks) + EMBEDDING_BATCH_SIZE - 1
        ) // EMBEDDING_BATCH_SIZE

        successful_chunks = 0
        failed_chunks = 0

        for batch_number, start in enumerate(
            range(0, len(chunks), EMBEDDING_BATCH_SIZE),
            start=1,
        ):
            batch = chunks[
                start : start + EMBEDDING_BATCH_SIZE
            ]

            try:
                embeddings = embed_texts(
                    [chunk[2] for chunk in batch]
                )

                vectors[start : start + len(batch)] = embeddings
                successful_chunks += len(batch)

                logger.info(
                    "Embedded batch %s/%s for document %s (%s chunks).",
                    batch_number,
                    total_batches,
                    document.id,
                    len(batch),
                )

            except Exception:
                failed_chunks += len(batch)

                logger.exception(
                    "Embedding failed for batch %s/%s of document %s. "
                    "Saving these chunks without vectors; lexical retrieval "
                    "will remain available.",
                    batch_number,
                    total_batches,
                    document.id,
                )

        logger.info(
            "Document %s embedding summary: %s successful, %s failed, "
            "%s total chunks.",
            document.id,
            successful_chunks,
            failed_chunks,
            len(chunks),
        )

    else:
        logger.warning(
            "Gemini is not configured. Document %s will be indexed "
            "without vector embeddings.",
            document.id,
        )

    for item, vector in zip(chunks, vectors, strict=True):
        chunk_index, page_number, content = item

        db.add(
            DocumentChunk(
                document_id=document.id,
                chunk_index=chunk_index,
                page_number=page_number,
                text_content=content,
                embedding=vector,
            )
        )
