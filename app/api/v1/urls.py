"""Shorten, preview, admin release, and the redirect hot path."""
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field, HttpUrl
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.v1.auth import current_user, optional_user, require_role
from app.core.database import Session, get_db
from app.models.orm import Click, LinkEmbedding, Url, User
from app.services import security as sec
from app.core.config import settings
from app.workers.tasks import _scan, scan_url

router = APIRouter(tags=["urls"])
redirect_router = APIRouter()

class ShortenIn(BaseModel):
    long_url: HttpUrl
    custom_code: str | None = Field(None, pattern=r"^[A-Za-z0-9_-]{3,32}$")
    tags: list[str] = []
    expires_in_hours: int | None = Field(None, ge=1, le=24 * 365)

@router.post("/api/v1/shorten", status_code=201)
async def shorten(b: ShortenIn, req: Request, bg: BackgroundTasks, db: AsyncSession = Depends(get_db), user: User | None = Depends(optional_user)) -> dict:
    try:
        sec.assert_public_url(str(b.long_url))
    except ValueError as e:
        raise HTTPException(400, str(e))
    code = b.custom_code or sec.new_code()
    if (await db.execute(select(Url.id).where(Url.short_code == code))).scalar():
        raise HTTPException(409, "Code taken")
    exp = datetime.now(timezone.utc) + timedelta(hours=b.expires_in_hours) if b.expires_in_hours else None
    row = Url(short_code=code, long_url=str(b.long_url), user_id=user.id if user else None, expires_at=exp)
    db.add(row); await db.commit()
    await sec.safe(req.app.state.redis.set(f"u:{code}", row.long_url, ex=86400))
    if settings.inline_agents:
        bg.add_task(_scan, row.id, row.long_url, b.tags)
    else:
        scan_url.delay(row.id, row.long_url, b.tags)  # Celery worker; may quarantine later
    return {"short_code": code, "short_url": f"/{code}", "status": "scanning"}

@router.get("/api/v1/links/{code}/preview")
async def preview(code: str, db: AsyncSession = Depends(get_db)) -> dict:
    q = select(LinkEmbedding.meta).join(Url).where(Url.short_code == code, Url.is_quarantined.is_(False)).limit(1)
    return (await db.execute(q)).scalar() or {}

@router.post("/api/v1/admin/release/{code}")
async def release(code: str, req: Request, db: AsyncSession = Depends(get_db), _: User = Depends(require_role("admin"))) -> dict:
    await db.execute(update(Url).where(Url.short_code == code).values(is_quarantined=False, threat_score=0))
    await db.commit(); await sec.safe(req.app.state.redis.delete(f"u:{code}"))
    return {"released": code}

async def log_click(code: str, ip: str, ua: str, ref: str, country: str | None) -> None:
    dev = "mobile" if "Mobi" in ua else "desktop"
    br = next((b for b in ("Edg", "Chrome", "Firefox", "Safari") if b in ua), "other")
    async with Session() as s:
        uid = (await s.execute(select(Url.id).where(Url.short_code == code))).scalar()
        if uid:
            s.add(Click(url_id=uid, country=country, device_type=dev, browser=br, ip_hash=sec.hash_ip(ip)))
            await s.execute(update(Url).where(Url.id == uid).values(click_count=Url.click_count + 1))
            await s.commit()

@redirect_router.get("/{code}")
async def go(code: str, req: Request, bg: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    r = req.app.state.redis
    dest = await sec.safe(r.get(f"u:{code}"))
    if not dest:
        u = (await db.execute(select(Url).where(Url.short_code == code))).scalar()
        now = datetime.now(timezone.utc)
        if not u or not u.is_active or u.is_quarantined:
            raise HTTPException(404, "Not found")
        if u.expires_at and u.expires_at < now:
            raise HTTPException(410, "Expired")
        dest = u.long_url
        await sec.safe(r.set(f"u:{code}", dest, ex=3600))  # warm cache
    ip = req.client.host if req.client else "0"
    bg.add_task(log_click, code, ip, req.headers.get("user-agent", ""), req.headers.get("referer", ""), req.headers.get("cf-ipcountry"))
    return RedirectResponse(dest, 307)

@router.get("/api/v1/links")
async def my_links(db: AsyncSession = Depends(get_db), u: User = Depends(current_user)) -> list[dict]:
    rows = (await db.execute(select(Url).where(Url.user_id == u.id).order_by(Url.created_at.desc()).limit(50))).scalars()
    return [{"code": r.short_code, "url": r.long_url, "clicks": r.click_count, "threat": r.threat_score, "quarantined": r.is_quarantined} for r in rows]

async def _own(db: AsyncSession, code: str, u: User) -> Url:
    url = (await db.execute(select(Url).where(Url.short_code == code, Url.user_id == u.id))).scalar()
    if not url:
        raise HTTPException(404, "Not found")
    return url

@router.get("/api/v1/links/{code}/stats")
async def link_stats(code: str, db: AsyncSession = Depends(get_db), u: User = Depends(current_user)) -> dict:
    url = await _own(db, code, u)
    rows = (await db.execute(select(Click.device_type, Click.country, func.count()).where(Click.url_id == url.id).group_by(Click.device_type, Click.country))).all()
    return {"code": code, "clicks": url.click_count, "breakdown": [{"device": d, "country": c, "count": n} for d, c, n in rows]}

@router.delete("/api/v1/links/{code}", status_code=204)
async def disable_link(code: str, req: Request, db: AsyncSession = Depends(get_db), u: User = Depends(current_user)) -> None:
    url = await _own(db, code, u)
    url.is_active = False
    await db.commit()
    await sec.safe(req.app.state.redis.delete(f"u:{code}"))
