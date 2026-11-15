"""FastAPI entrypoint: routers, CORS, per-IP rate limiting, request IDs, schema bootstrap."""
import uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import CONTENT_TYPE_LATEST, Counter, generate_latest
from redis.asyncio import Redis
from sqlalchemy import text
from app.api.v1 import analytics, auth, urls
from app.core.config import settings
from app.core.database import engine
from app.models.orm import Base
from app.services import llm, security as sec

REQS = Counter("http_requests_total", "Requests", ["route", "status"])

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.redis = Redis.from_url(settings.redis_url, decode_responses=True)
    async with engine.begin() as c:
        await c.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await c.run_sync(Base.metadata.create_all)
    yield
    await app.state.redis.aclose()

app = FastAPI(title="LinkSentinel", version="1.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()], allow_origin_regex=settings.cors_regex, allow_methods=["*"], allow_headers=["*"])

@app.middleware("http")
async def guard(req: Request, call_next):
    ip = req.client.host if req.client else "0"
    if not await sec.allow(app.state.redis, sec.hash_ip(ip), settings.rate_limit):
        return JSONResponse({"detail": "rate limited"}, 429)
    res = await call_next(req)
    route = req.scope.get("route")
    REQS.labels(route.path if route else "unmatched", res.status_code).inc()
    res.headers["X-Request-ID"] = str(uuid.uuid4())
    res.headers.update({"X-Content-Type-Options": "nosniff", "X-Frame-Options": "DENY", "Referrer-Policy": "no-referrer", "Strict-Transport-Security": "max-age=31536000; includeSubDomains", "Permissions-Policy": "camera=(), microphone=(), geolocation=()"})
    return res

@app.post("/api/v1/assistant/chat")
async def assistant(body: dict) -> dict:
    return {"answer": await llm.complete("You are Sentinel, assistant for the LinkSentinel platform. Be concise.", body["messages"])}

@app.get("/metrics", include_in_schema=False)
async def metrics():
    from fastapi.responses import Response
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.get("/healthz")
async def healthz() -> dict:
    return {"ok": True, "redis": bool(await sec.safe(app.state.redis.ping(), False))}

app.include_router(auth.router)
app.include_router(analytics.router)
app.include_router(urls.router)
app.include_router(urls.redirect_router)  # catch-all last
