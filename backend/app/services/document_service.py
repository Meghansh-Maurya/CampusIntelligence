from __future__ import annotations
import logging, re, threading, uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import pymupdf as fitz
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models import Document, DocumentChunk
from app.services.ai_service import ai_is_configured, embed_texts

logger = logging.getLogger(__name__)
EMBEDDING_BATCH_SIZE = 32
EMBEDDING_WORKERS = 4
_OCR_ENGINE = None
_OCR_LOCK = threading.Lock()

def split_text(text: str, chunk_size: int = 1200, overlap: int = 180) -> list[str]:
    clean = re.sub(r"\s+", " ", text).strip()
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

def _get_ocr_engine():
    global _OCR_ENGINE
    try:
        from rapidocr_onnxruntime import RapidOCR
    except ImportError as exc:
        raise ValueError("Scanned PDF detected. Install rapidocr-onnxruntime from backend requirements.txt to enable OCR.") from exc
    with _OCR_LOCK:
        if _OCR_ENGINE is None:
            _OCR_ENGINE = RapidOCR()
    return _OCR_ENGINE


def _order_ocr_items(result) -> tuple[str, float | None]:
    """Turn RapidOCR boxes into text in reading order (top-to-bottom, left-to-right)."""
    items = []
    for item in result or []:
        if len(item) < 3 or not str(item[1]).strip():
            continue
        try:
            xs = [pt[0] for pt in item[0]]
            ys = [pt[1] for pt in item[0]]
            top, left, height = min(ys), min(xs), max(ys) - min(ys)
        except (TypeError, IndexError):
            top, left, height = 0.0, 0.0, 1.0
        try:
            score = float(item[2])
        except (TypeError, ValueError):
            score = None
        items.append((top, left, max(height, 1.0), str(item[1]).strip(), score))
    if not items:
        return "", None
    items.sort(key=lambda x: (x[0], x[1]))
    rows: list[list[tuple]] = []
    for it in items:
        if rows and abs(it[0] - rows[-1][0][0]) <= 0.6 * max(it[2], rows[-1][0][2]):
            rows[-1].append(it)
        else:
            rows.append([it])
    lines = [" ".join(x[3] for x in sorted(row, key=lambda x: x[1])) for row in rows]
    scores = [x[4] for x in items if x[4] is not None]
    return "\n".join(lines), (sum(scores) / len(scores) if scores else None)


def _ocr_image(image_bytes: bytes) -> tuple[str, float | None]:
    engine = _get_ocr_engine()
    result, _ = engine(image_bytes)
    return _order_ocr_items(result)


def extract_pdf_pages_with_metadata(file_path: Path) -> tuple[list[tuple[int, str]], dict]:
    pages, ocr_pages, confidence = [], [], {}
    try:
        with fitz.open(file_path) as pdf:
            if len(pdf) > settings.max_pdf_pages: raise ValueError(f"PDF exceeds {settings.max_pdf_pages} pages.")
            if pdf.is_encrypted: raise ValueError("Password-protected PDFs are not supported.")
            for i, page in enumerate(pdf):
                native = page.get_text("text", sort=True).strip()
                compact = re.sub(r"\s+", "", native)
                usable = len(compact) >= 35 and sum(c.isalnum() for c in compact) / max(len(compact), 1) >= .35
                text = native
                if not usable:
                    pix = page.get_pixmap(matrix=fitz.Matrix(220/72, 220/72), colorspace=fitz.csRGB, alpha=False)
                    ocr_text, score = _ocr_image(pix.tobytes("png"))
                    if ocr_text.strip() and len(ocr_text.strip()) > len(native):
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
    if ai_is_configured() and chunks:
        def embed_batch(start: int):
            batch = chunks[start:start + EMBEDDING_BATCH_SIZE]
            try:
                embedded = embed_texts([x[2] for x in batch], task_type="RETRIEVAL_DOCUMENT")
                if any(len(v) != settings.gemini_embedding_dimensions for v in embedded):
                    raise ValueError("Embedding dimension mismatch.")
                return start, embedded
            except Exception:
                logger.exception("Embedding batch starting at chunk %s failed for document %s; retaining lexical chunks.", start, document.id)
                return start, None

        starts = range(0, len(chunks), EMBEDDING_BATCH_SIZE)
        with ThreadPoolExecutor(max_workers=EMBEDDING_WORKERS) as pool:
            for start, embedded in pool.map(embed_batch, starts):
                if embedded is not None:
                    vectors[start:start + len(embedded)] = embedded
    elif not ai_is_configured():
        logger.warning("Gemini unavailable; document %s will use lexical retrieval.", document.id)
    for item, vector in zip(chunks, vectors, strict=True):
        idx, page, content = item
        db.add(DocumentChunk(document_id=document.id, chunk_index=idx, page_number=page, text_content=content, embedding=vector))
