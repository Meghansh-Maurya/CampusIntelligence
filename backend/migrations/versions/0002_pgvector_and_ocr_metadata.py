"""Move JSON embeddings to pgvector and add document extraction metadata."""
from alembic import op
import sqlalchemy as sa

revision = "0002_pgvector_ocr"
down_revision = "0001_initial"
branch_labels = None
depends_on = None
DIMENSIONS = 768

def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.alter_column("document_chunks", "embedding", new_column_name="embedding_legacy")
    op.execute(f"ALTER TABLE document_chunks ADD COLUMN embedding vector({DIMENSIONS})")
    op.execute(f"""
        UPDATE document_chunks
        SET embedding = embedding_legacy::text::vector({DIMENSIONS})
        WHERE embedding_legacy IS NOT NULL
          AND jsonb_typeof(embedding_legacy::jsonb) = 'array'
          AND jsonb_array_length(embedding_legacy::jsonb) = {DIMENSIONS}
    """)
    op.add_column("documents", sa.Column("extraction_metadata", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")))
    op.create_index("ix_document_chunks_embedding_hnsw", "document_chunks", ["embedding"], postgresql_using="hnsw", postgresql_with={"m": 16, "ef_construction": 64}, postgresql_ops={"embedding": "vector_cosine_ops"})

def downgrade() -> None:
    op.drop_index("ix_document_chunks_embedding_hnsw", table_name="document_chunks")
    op.drop_column("documents", "extraction_metadata")
    op.drop_column("document_chunks", "embedding")
    op.alter_column("document_chunks", "embedding_legacy", new_column_name="embedding")
