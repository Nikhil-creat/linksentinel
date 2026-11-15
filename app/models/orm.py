"""SQLAlchemy 2.0 models incl. pgvector embeddings."""
from datetime import datetime
from sqlalchemy import ForeignKey, String, Text, Float, Boolean, DateTime, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from pgvector.sqlalchemy import Vector

class Base(DeclarativeBase): ...

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    api_key: Mapped[str | None] = mapped_column(String(64), unique=True)
    tier: Mapped[str] = mapped_column(String(16), default="free")
    role: Mapped[str] = mapped_column(String(16), default="free")

class Url(Base):
    __tablename__ = "urls"
    id: Mapped[int] = mapped_column(primary_key=True)
    short_code: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    long_url: Mapped[str] = mapped_column(Text)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    click_count: Mapped[int] = mapped_column(default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_quarantined: Mapped[bool] = mapped_column(Boolean, default=False)
    threat_score: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

class Click(Base):
    __tablename__ = "clicks"
    id: Mapped[int] = mapped_column(primary_key=True)
    url_id: Mapped[int] = mapped_column(ForeignKey("urls.id"), index=True)
    clicked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    country: Mapped[str | None] = mapped_column(String(2))
    device_type: Mapped[str | None] = mapped_column(String(16))
    browser: Mapped[str | None] = mapped_column(String(32))
    ip_hash: Mapped[str] = mapped_column(String(64))

class LinkEmbedding(Base):
    __tablename__ = "link_embeddings"
    id: Mapped[int] = mapped_column(primary_key=True)
    url_id: Mapped[int] = mapped_column(ForeignKey("urls.id"), index=True)
    content_chunk: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float]] = mapped_column(Vector(768))
    meta: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)
