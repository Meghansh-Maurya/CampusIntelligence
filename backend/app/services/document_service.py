from __future__ import annotations
import logging, re, uuid
from pathlib import Path
import pymupdf as fitz
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models import Document, DocumentChunk
from app.services.ai_service import ai_is_configured, embed_texts

logger = logging.getLogger(__name__)
EMBEDDING_BATCH_SIZE = 8
_OCR_ENGINE = None

def split_text(text: str, chunk_size: int = 1200, overlap: int = 180) -> list[str]:
    clean = re.sub(r"\\s+", " ", text).strip()
    if not clean: return []
    if chunk_size <= 0 or overlap < 0 or overlap >= chunk_size: raise ValueError("Invalid chunk size/overlap.")
    chunks, start = [], 0
    while start < len(clean):
        end = min(start + chunk_size, len(clean))
        if end < len(clean):
            boundary = clean.rfind(" ", start + int(chunk_size * .65), end)
            if boundary > start: end = boundary
        piece = clean[start:end].strip()
        if piece: chunks.append(piece)
        if end >= len(clean): break
        start = max(end - overlap, start + 1)
    return chunks

def _ocr_image(image_bytes: bytes) -> tuple[str, float | None]:
    global _OCR_ENGINE
    try:
        from rapidocr_onnxruntime import RapidOCR
    except ImportError as exc:
        raise ValueError("Scanned PDF detected. Install rapidocr-onnxruntime from backend requirements.txt to enable OCR.") from exc
    if _OCR_ENGINE is None: _OCR_ENGINE = RapidOCR()
    result, _ = _OCR_ENGINE(image_bytes)
    if not result: return "", None
    lines, scores = [], []
    for item in result:
        if len(item) >= 3 and str(item[1]).strip():
            lines.append(str(item[1]).strip())
            try: scores.append(float(item[2]))
            except (TypeError, ValueError): pass
    return "\\n".join(lines), (sum(scores) / len(scores) if scores else None)

def extract_pdf_pages_with_metadata(file_path: Path) -> tuple[list[tuple[int, str]], dict]:
    pages, ocr_pages, confidence = [], [], {}
    try:
        with fitz.open(file_path) as pdf:
            if len(pdf) > settings.max_pdf_pages: raise ValueError(f"PDF exceeds {settings.max_pdf_pages} pages.")
            if pdf.is_encrypted: raise ValueError("Password-protected PDFs are not supported.")
            for i, page in enumerate(pdf):
                native = page.get_text("text").strip()
                compact = re.sub(r"\\s+", "", native)
                usable = len(compact) >= 35 and sum(c.isalnum() for c in compact) / max(len(compact), 1) >= .35
                text = native
                if not usable:
                    pix = page.get_pixmap(matrix=fitz.Matrix(220/72, 220/72), colorspace=fitz.csRGB, alpha=False)
                    ocr_text, score = _ocr_image(pix.tobytes("png"))
                    if ocr_text.strip():
                        text = ocr_text.strip()
                        ocr_pages.append(i + 1)
                        if score is not None: confidence[str(i + 1)] = round(score, 4)
                pages.append((i + 1, text))
    except ValueError: raise
    except Exception as exc: raise ValueError("This file could not be read as a valid PDF.") from exc
    if not pages or not any(t.strip() for _, t in pages):
        raise ValueError("No readable text could be extracted. The PDF may be blank, damaged, or too low-quality for OCR.")
    return pages, {"extraction_method": "mixed" if ocr_pages and len(ocr_pages) < len(pages) else ("ocr" if ocr_pages else "native"), "ocr_pages": ocr_pages, "ocr_engine": "RapidOCR" if ocr_pages else None, "ocr_average_confidence_by_page": confidence, "page_count": len(pages)}

def extract_pdf_pages(file_path: Path) -> list[tuple[int, str]]:
    return extract_pdf_pages_with_metadata(file_path)[0]

def make_page_chunks(pages: list[tuple[int, str]]) -> list[tuple[int, int, str]]:
    out, idx = [], 0
    for page, text in pages:
        for part in split_text(text):
            out.append((idx, page, part)); idx += 1
    return out

def save_document_file(contents: bytes) -> tuple[str, Path]:
    settings.storage_dir.mkdir(parents=True, exist_ok=True)
    name = f"{uuid.uuid4().hex}.pdf"
    path = settings.storage_dir / name
    path.write_bytes(contents)
    return name, path

def index_document_chunks(db: Session, document: Document, chunks: list[tuple[int, int, str]]) -> None:
    vectors: list[list[float] | None] = [None] * len(chunks)
    if ai_is_configured():
        for start in range(0, len(chunks), EMBEDDING_BATCH_SIZE):
            batch = chunks[start:start + EMBEDDING_BATCH_SIZE]
            try:
                embedded = embed_texts([x[2] for x in batch], task_type="RETRIEVAL_DOCUMENT")
                if any(len(v) != settings.gemini_embedding_dimensions for v in embedded):
                    raise ValueError("Embedding dimension mismatch.")
                vectors[start:start + len(batch)] = embedded
            except Exception:
                logger.exception("Embedding batch failed for document %s; retaining lexical chunks.", document.id)
    else:
        logger.warning("Gemini unavailable; document %s will use lexical retrieval.", document.id)
    for item, vector in zip(chunks, vectors, strict=True):
        idx, page, content = item
        db.add(DocumentChunk(document_id=document.id, chunk_index=idx, page_number=page, text_content=content, embedding=vector))
