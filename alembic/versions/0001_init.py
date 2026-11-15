"""initial schema + pgvector"""
from alembic import op
from app.models.orm import Base

revision, down_revision = "0001", None

def upgrade():
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    Base.metadata.create_all(bind=op.get_bind())

def downgrade():
    Base.metadata.drop_all(bind=op.get_bind())
