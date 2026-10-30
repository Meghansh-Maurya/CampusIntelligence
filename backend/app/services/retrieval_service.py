from __future__ import annotations

import math
import re
import logging
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
STOP_WORDS = {
    "about", "after", "again", "also", "and", "are", "can", "could", "does", "explain", "for", "from",
    "have", "into", "is", "its", "make", "more", "most", "not", "our", "please", "show", "that", "the",
    "their", "these", "this", "through", "what", "when", "where", "which", "with", "would", "you", "your",
}


@dataclass
class RetrievedChunk:
    chunk: DocumentChunk
    document: Document
    score: float


def _tokens(text: str) -> set[str]:
    return {token.lower() for token in re.findall(r"[A-Za-z][A-Za-z0-9+#.-]{1,}", text) if token.lower() not in STOP_WORDS}


def _lexical_score(question: str, passage: str) -> float:
    q_tokens = _tokens(question)
    if not q_tokens:
        return 0.0
    p_tokens = _tokens(passage)
    return len(q_tokens & p_tokens) / len(q_tokens)


def _cosine(left: list[float], right: list[float]) -> float:
    if not left or len(left) != len(right):
        return 0.0
    dot = sum(a * b for a, b in zip(left, right, strict=True))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if not left_norm or not right_norm:
        return 0.0
    return dot / (left_norm * right_norm)


def retrieve_chunks(
    db: Session,
    user_id: UUID,
    question: str,
    document_ids: list[UUID] | None = None,
    top_k: int = 6,
) -> list[RetrievedChunk]:
    stmt = (
        select(DocumentChunk, Document)
        .join(Document, Document.id == DocumentChunk.document_id)
        .where(
            Document.user_id == user_id,
            Document.status == "ready",
            Document.document_type.in_(ACADEMIC_TYPES),
        )
    )
    if document_ids is not None:
        if not document_ids:
            return []
        owned_docs = db.scalars(
            select(Document).where(Document.id.in_(document_ids), Document.user_id == user_id, Document.document_type.in_(ACADEMIC_TYPES))
        ).all()
        if len({doc.id for doc in owned_docs}) != len(set(document_ids)):
            raise HTTPException(status_code=404, detail="One or more selected academic documents do not exist or are not accessible.")
        stmt = stmt.where(Document.id.in_(document_ids))

    pairs = db.execute(stmt.limit(settings.max_document_chunks_for_retrieval)).all()
    if not pairs:
        return []

    query_vector: list[float] | None = None
    if ai_is_configured():
        try:
            query_vector = embed_texts([question])[0]
        except Exception:
            logger.exception("Query embedding failed; using lexical retrieval")

    scored: list[RetrievedChunk] = []
    for chunk, document in pairs:
        lexical = _lexical_score(question, chunk.text_content)
        if query_vector and chunk.embedding:
            semantic = max(0.0, _cosine(query_vector, chunk.embedding))
            score = semantic + 0.2 * lexical
            # Don't send obviously unrelated passages just because every vector has a score.
            if semantic < 0.25 and lexical <= 0.0:
                continue
        else:
            score = lexical
            # With lexical-only retrieval, zero overlap is not evidence.
            if lexical <= 0.0:
                continue
        scored.append(RetrievedChunk(chunk=chunk, document=document, score=score))
    scored.sort(key=lambda item: item.score, reverse=True)
    return scored[:top_k]
