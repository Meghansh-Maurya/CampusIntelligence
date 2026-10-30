from pathlib import Path

ROOT = Path(__file__).resolve().parent
MODELS = ROOT / "backend/app/models.py"
ROUTES = ROOT / "backend/app/routes/documents.py"
REQ = ROOT / "backend/requirements.txt"

def once(text, old, new, label):
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one match, found {count}; no safe patch.")
    return text.replace(old, new, 1)

m = MODELS.read_text(encoding="utf-8")
m = once(m,
    "from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship\n",
    "from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship\nfrom pgvector.sqlalchemy import Vector\n",
    "SQLAlchemy import")
m = once(m,
    '    extracted_text: Mapped[str] = mapped_column(Text, default="")\n',
    '    extracted_text: Mapped[str] = mapped_column(Text, default="")\n    extraction_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)\n',
    "Document extraction metadata")
m = once(m,
    '    # JSON embeddings keep first-time local setup simple. For high-volume production,\n    # migrate this column to pgvector and perform similarity search in PostgreSQL.\n    embedding: Mapped[list[float] | None] = mapped_column(JSON, nullable=True)\n',
    '    # Must match GEMINI_EMBEDDING_DIMENSIONS and migration 0002.\n    embedding: Mapped[list[float] | None] = mapped_column(Vector(768), nullable=True)\n',
    "DocumentChunk embedding")
MODELS.write_text(m, encoding="utf-8")

r = ROUTES.read_text(encoding="utf-8")
r = once(r,
    "from app.services.document_service import extract_pdf_pages, index_document_chunks, make_page_chunks, save_document_file\n",
    "from app.services.document_service import extract_pdf_pages_with_metadata, index_document_chunks, make_page_chunks, save_document_file\n",
    "document service import")
r = once(r, "        pages = extract_pdf_pages(path)\n",
    "        pages, extraction_metadata = extract_pdf_pages_with_metadata(path)\n", "PDF extraction")
r = once(r, '            extracted_text=extracted_text,\n',
    '            extracted_text=extracted_text,\n            extraction_metadata=extraction_metadata,\n', "document metadata")
old = '''    except Exception:
        db.rollback()
        # The first insert may already have committed before chunk indexing. Remove the partial record.
        try:
            if "document" in locals():
                existing = db.get(Document, document.id)
                if existing is not None:
                    db.delete(existing)
                    db.commit()
        except Exception:
            db.rollback()
            logger.exception("Could not remove partial document record")
        path.unlink(missing_ok=True)
        logger.exception("Failed to process an uploaded document")
        raise HTTPException(status_code=500, detail="The document could not be processed. Check backend logs.")
'''
new = '''    except Exception:
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
'''
r = once(r, old, new, "upload failure preservation")
ROUTES.write_text(r, encoding="utf-8")

req = REQ.read_text(encoding="utf-8")
for line in ["pgvector>=0.3.6,<1.0", "rapidocr-onnxruntime>=1.3.24,<2.0"]:
    if line.split(">=")[0] not in req:
        req += line + "\n"
REQ.write_text(req, encoding="utf-8")
print("Patched models.py, routes/documents.py, and requirements.txt.")