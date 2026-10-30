from __future__ import annotations

import logging
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.security import get_current_user
from app.models import Document, User
from app.schemas import DocumentRead
from app.services.document_service import extract_pdf_pages_with_metadata, index_document_chunks, make_page_chunks, save_document_file

logger = logging.getLogger(__name__)
router = APIRouter()
ALLOWED_DOCUMENT_TYPES = {
    "syllabus",
    "notes",
    "previous_year_paper",
    "placement_notification",
    "job_description",
    "resume",
}


@router.post("", response_model=DocumentRead, status_code=status.HTTP_201_CREATED)
def upload_document(
    file: UploadFile = File(...),
    document_type: str = Form(...),
    subject: str | None = Form(default=None, max_length=160),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Document:
    if document_type not in ALLOWED_DOCUMENT_TYPES:
        raise HTTPException(status_code=422, detail=f"document_type must be one of: {', '.join(sorted(ALLOWED_DOCUMENT_TYPES))}.")
    if not file.filename:
        raise HTTPException(status_code=422, detail="A filename is required.")
    safe_name = file.filename.replace("\\", "/").split("/")[-1].strip()[:255]
    if not safe_name:
        raise HTTPException(status_code=422, detail="The filename is invalid.")
    if Path(safe_name).suffix.lower() != ".pdf":
        raise HTTPException(status_code=415, detail="Only PDF uploads are supported in this version.")

    contents = file.file.read(settings.max_upload_mb * 1024 * 1024 + 1)
    if not contents:
        raise HTTPException(status_code=422, detail="The uploaded file is empty.")
    if len(contents) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"Maximum upload size is {settings.max_upload_mb} MB.")
    if not contents.startswith(b"%PDF-"):
        raise HTTPException(status_code=415, detail="The uploaded file does not look like a PDF.")

    stored_filename, path = save_document_file(contents)
    try:
        pages, extraction_metadata = extract_pdf_pages_with_metadata(path)
        extracted_text = "\n\n".join(f"[Page {page_number}]\n{text}" for page_number, text in pages if text)
        chunks = make_page_chunks(pages)
        document = Document(
            user_id=current_user.id,
            original_filename=safe_name,
            stored_filename=stored_filename,
            document_type=document_type,
            subject=subject.strip() if subject else None,
            content_type="application/pdf",
            file_size_bytes=len(contents),
            page_count=len(pages),
            status="processing",
            extracted_text=extracted_text,
            extraction_metadata=extraction_metadata,
        )
        db.add(document)
        db.commit()
        db.refresh(document)
        index_document_chunks(db, document, chunks)
        document.status = "ready"
        db.commit()
        db.refresh(document)
        return document
    except ValueError as exc:
        db.rollback()
        try:
            if "document" in locals():
                existing = db.get(Document, document.id)
                if existing is not None:
                    db.delete(existing)
                    db.commit()
        except Exception:
            db.rollback()
            logger.exception("Could not remove partial document record after validation failure")
        path.unlink(missing_ok=True)
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception:
        db.rollback()
        # The document row and extracted text were committed before chunk indexing.
        # Preserve the source file and document so it can still be accessed/reindexed.
        if "document" in locals():
            try:
                existing = db.get(Document, document.id)
                if existing is not None:
                    existing.status = "ready"
                    db.commit()
                    db.refresh(existing)
                    logger.exception("Chunk indexing failed for %s; preserving document for recovery.", existing.id)
                    return existing
            except Exception:
                db.rollback()
        path.unlink(missing_ok=True)
        logger.exception("Failed to process an uploaded document")
        raise HTTPException(status_code=500, detail="The document could not be processed. Check backend logs.")
    finally:
        file.file.close()


@router.get("", response_model=list[DocumentRead])
def list_documents(
    document_type: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Document]:
    stmt = select(Document).where(Document.user_id == current_user.id).order_by(Document.created_at.desc())
    if document_type:
        if document_type not in ALLOWED_DOCUMENT_TYPES:
            raise HTTPException(status_code=422, detail="Unknown document_type.")
        stmt = stmt.where(Document.document_type == document_type)
    return list(db.scalars(stmt).all())


@router.get("/{document_id}", response_model=DocumentRead)
def get_document(
    document_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Document:
    document = db.scalar(select(Document).where(Document.id == document_id, Document.user_id == current_user.id))
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found.")
    return document


@router.get("/{document_id}/download")
def download_document(
    document_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FileResponse:
    document = db.scalar(select(Document).where(Document.id == document_id, Document.user_id == current_user.id))
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found.")
    path = settings.storage_dir / document.stored_filename
    if not path.is_file():
        raise HTTPException(status_code=404, detail="The stored file is missing.")
    return FileResponse(path, media_type="application/pdf", filename=document.original_filename)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    document = db.scalar(select(Document).where(Document.id == document_id, Document.user_id == current_user.id))
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found.")
    path = settings.storage_dir / document.stored_filename
    db.delete(document)
    db.commit()
    try:
        path.unlink(missing_ok=True)
    except OSError:
        logger.exception("Could not remove stored file for document %s", document_id)
