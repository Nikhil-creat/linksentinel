"""Celery agents. A1: reputation/redirect-chain heuristics. A2: CNN visual stub. A3: OpenGraph + embedding."""
import asyncio, re
from urllib.parse import urlparse
import httpx
from celery import Celery
from sqlalchemy import update
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from app.core.config import settings
from app.models.orm import LinkEmbedding, Url
from app.services import llm, security as sec

celery = Celery("ls", broker=settings.redis_url)
SUSPECT = ("login", "verify", "secure", "account", "update", "wallet")

from app.services.cnn import spoof_score as cnn_spoof_score

async def crawl(url: str) -> tuple[str, int]:
    """SSRF-safe manual redirect walk (max 5 hops); returns html and hop count."""
    async with httpx.AsyncClient(follow_redirects=False, timeout=8) as c:
        for hop in range(6):
            sec.assert_public_url(url)
            r = await c.get(url, headers={"User-Agent": "LinkSentinelBot"})
            if r.is_redirect and r.headers.get("location"):
                url = str(r.url.join(r.headers["location"])); continue
            return r.text[:200_000], hop
    return "", 6

def heuristic(url: str, hops: int) -> float:
    host = urlparse(url).hostname or ""
    s = 0.3 if re.fullmatch(r"[\d.]+", host) else 0.0
    s += 0.3 if "xn--" in host else 0.0
    s += 0.2 if host.count(".") >= 4 else 0.0
    s += 0.15 if any(k in url.lower() for k in SUSPECT) else 0.0
    return min(1.0, s + 0.1 * max(0, hops - 1))

def og(html: str, prop: str) -> str:
    m = re.search(rf'<meta[^>]+property=["\']og:{prop}["\'][^>]+content=["\']([^"\']+)', html, re.I)
    return m.group(1) if m else ""

async def _scan(url_id: int, url: str, tags: list[str]) -> dict:
    try:
        html, hops = await crawl(url)
    except ValueError:  # redirect into private space or bad scheme
        html, hops = "", 3
    except Exception:  # timeout / bot-blocked: unknown, not suspicious
        html, hops = "", 0
    score = max(heuristic(url, hops), cnn_spoof_score(b""))
    title = og(html, "title") or (re.search(r"<title>(.*?)</title>", html, re.I | re.S) or [None, ""])[1].strip()
    desc = og(html, "description")
    quarantine = score >= 0.7
    eng = create_async_engine(settings.database_url, poolclass=NullPool)
    async with async_sessionmaker(eng)() as s:
        await s.execute(update(Url).where(Url.id == url_id).values(threat_score=score, is_quarantined=quarantine))
        if not quarantine:
            text = f"{title}. {desc}. url={url} tags={','.join(tags)}"
            s.add(LinkEmbedding(url_id=url_id, content_chunk=text, embedding=await llm.embed(text), meta={"title": title, "description": desc, "image": og(html, "image"), "tags": tags}))
        await s.commit()
    await eng.dispose()
    return {"url_id": url_id, "threat_score": score, "quarantine": quarantine}

@celery.task
def scan_url(url_id: int, long_url: str, tags: list[str] | None = None) -> dict:
    return asyncio.run(_scan(url_id, long_url, tags or []))
