from __future__ import annotations
import logging, re
from dataclasses import dataclass
from uuid import UUID
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models import Document, DocumentChunk
from app.services.ai_service import ai_is_configured, embed_texts

logger = logging.getLogger(__name__)
ACADEMIC_TYPES = {"syllabus", "notes", "previous_year_paper"}
STOP_WORDS = {"about","after","again","also","and","are","can","could","does","explain","for","from","have","into","is","its","make","more","most","not","our","please","show","that","the","their","these","this","through","what","when","where","which","with","would","you","your"}

@dataclass
class RetrievedChunk:
    chunk: DocumentChunk
    document: Document
    score: float

def _tokens(text: str) -> set[str]:
    return {t.lower() for t in re.findall(r"[A-Za-z][A-Za-z0-9+#.-]{1,}", text) if t.lower() not in STOP_WORDS}

def _lexical_score(question: str, passage: str) -> float:
    q = _tokens(question)
    return len(q & _tokens(passage)) / len(q) if q else 0.0

def retrieve_chunks(db: Session, user_id: UUID, question: str, document_ids: list[UUID] | None = None, top_k: int = 6) -> list[RetrievedChunk]:
    if document_ids is not None:
        if not document_ids:
            return []
        ids = set(document_ids)
        owned = db.scalars(select(Document).where(Document.id.in_(ids), Document.user_id == user_id, Document.document_type.in_(ACADEMIC_TYPES), Document.status == "ready")).all()
        if {d.id for d in owned} != ids:
            raise HTTPException(status_code=404, detail="One or more selected academic documents do not exist or are not accessible.")
    base = select(DocumentChunk, Document).join(Document, Document.id == DocumentChunk.document_id).where(Document.user_id == user_id, Document.status == "ready", Document.document_type.in_(ACADEMIC_TYPES))
    if document_ids is not None:
        base = base.where(Document.id.in_(set(document_ids)))
    qvec = None
    if ai_is_configured():
        try:
            qvec = embed_texts([question], task_type="RETRIEVAL_QUERY")[0]
            if len(qvec) != settings.gemini_embedding_dimensions:
                raise ValueError("Query embedding dimension does not match configured pgvector dimension.")
        except Exception:
            logger.exception("Query embedding failed; using lexical retrieval")
    vector_rows = []
    if qvec is not None:
        try:
            distance = DocumentChunk.embedding.cosine_distance(qvec)
            vector_stmt = (
                base.with_only_columns(DocumentChunk, Document, distance.label("distance"))
                .where(DocumentChunk.embedding.is_not(None))
                .order_by(distance.asc())
                .limit(max(top_k * 8, 40))
            )
            vector_rows = db.execute(vector_stmt).all()
        except Exception:
            db.rollback()
            logger.exception("pgvector query failed; falling back to lexical retrieval")
    lexical_rows = db.execute(base.limit(min(settings.max_document_chunks_for_retrieval, max(top_k * 20, 100)))).all()
    merged = {}
    for chunk, doc, dist in vector_rows:
        # PostgreSQL returns cosine distance with each candidate; no per-row query.
        semantic = max(0.0, 1.0 - float(dist)) if dist is not None else 0.0
        merged[chunk.id] = (chunk, doc, semantic, _lexical_score(question, chunk.text_content))
    for chunk, doc in lexical_rows:
        lexical = _lexical_score(question, chunk.text_content)
        if chunk.id in merged:
            old = merged[chunk.id]
            merged[chunk.id] = (chunk, doc, old[2], lexical)
        elif lexical > 0:
            merged[chunk.id] = (chunk, doc, 0.0, lexical)
    results = []
    for chunk, doc, semantic, lexical in merged.values():
        score = 0.75 * semantic + 0.25 * lexical if qvec is not None and chunk.embedding is not None else lexical
        if score > 0:
            results.append(RetrievedChunk(chunk, doc, score))
    return sorted(results, key=lambda x: x.score, reverse=True)[:top_k]
