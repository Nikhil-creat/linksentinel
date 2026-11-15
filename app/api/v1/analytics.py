"""RAG analytics: hybrid retrieval (pgvector cosine + per-user filter + live click aggregates) -> grounded LLM answer."""
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.v1.auth import current_user
from app.core.database import get_db
from app.models.orm import Click, LinkEmbedding, Url, User
from app.services import llm

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])

class AskIn(BaseModel):
    question: str = Field(min_length=3, max_length=500)
    days: int = Field(7, ge=1, le=90)

@router.get("/summary")
async def summary(db: AsyncSession = Depends(get_db), u: User = Depends(current_user)) -> dict:
    q = select(func.count(Url.id), func.coalesce(func.sum(Url.click_count), 0), func.count(Url.id).filter(Url.is_quarantined)).where(Url.user_id == u.id)
    links, clicks, quarantined = (await db.execute(q)).one()
    return {"links": links, "clicks": int(clicks), "quarantined": quarantined}

@router.post("/chat")
async def chat(b: AskIn, db: AsyncSession = Depends(get_db), u: User = Depends(current_user)) -> dict:
    qv = await llm.embed(b.question)
    since = datetime.now(timezone.utc) - timedelta(days=b.days)
    chunks = (await db.execute(select(LinkEmbedding.content_chunk, Url.short_code).join(Url).where(Url.user_id == u.id).order_by(LinkEmbedding.embedding.cosine_distance(qv)).limit(5))).all()
    agg = (await db.execute(select(Url.short_code, Click.country, Click.device_type, func.count()).join(Url).where(Url.user_id == u.id, Click.clicked_at >= since).group_by(Url.short_code, Click.country, Click.device_type).order_by(func.count().desc()).limit(40))).all()
    ctx = "LINKS:\n" + "\n".join(f"[{c}] {t}" for t, c in chunks) + "\nCLICKS (code,country,device,count):\n" + "\n".join(map(str, agg))
    ans = await llm.complete("Answer ONLY from the context. If it lacks the answer, say so. Cite short codes.", [{"role": "user", "content": f"{ctx}\n\nQuestion: {b.question}"}])
    return {"answer": ans, "sources": [c for _, c in chunks]}
