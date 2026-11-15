"""Auto-detecting Groq/Gemini client: provider from configured key, live model discovery."""
import httpx
from app.core.config import settings

async def _detect(c: httpx.AsyncClient):
    if settings.groq_api_key:
        r = (await c.get("https://api.groq.com/openai/v1/models", headers={"Authorization": f"Bearer {settings.groq_api_key}"})).json()
        ids = [m["id"] for m in r["data"] if not any(x in m["id"] for x in ("whisper", "guard", "tts"))]
        return "groq", next((i for i in ids if "70b" in i), ids[0])
    r = (await c.get(f"https://generativelanguage.googleapis.com/v1beta/models?key={settings.gemini_api_key}")).json()
    ids = [m["name"].split("/")[1] for m in r["models"] if "generateContent" in m.get("supportedGenerationMethods", [])]
    return "gemini", next((i for i in ids if "flash" in i), ids[0])

async def complete(system: str, messages: list[dict]) -> str:
    if not (settings.groq_api_key or settings.gemini_api_key):
        from fastapi import HTTPException
        raise HTTPException(503, "No GROQ_API_KEY or GEMINI_API_KEY configured on the server")
    async with httpx.AsyncClient(timeout=30) as c:
        p, m = await _detect(c)
        if p == "groq":
            r = await c.post("https://api.groq.com/openai/v1/chat/completions", headers={"Authorization": f"Bearer {settings.groq_api_key}"}, json={"model": m, "messages": [{"role": "system", "content": system}, *messages]})
            return r.json()["choices"][0]["message"]["content"]
        body = {"systemInstruction": {"parts": [{"text": system}]}, "contents": [{"role": "user" if x["role"] == "user" else "model", "parts": [{"text": x["content"]}]} for x in messages]}
        r = await c.post(f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={settings.gemini_api_key}", json=body)
        return r.json()["candidates"][0]["content"]["parts"][0]["text"]

async def embed(text: str) -> list[float]:
    """768-dim embedding via Gemini text-embedding-004; deterministic hash fallback when no key (dev only)."""
    if settings.gemini_api_key:
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.post(f"https://generativelanguage.googleapis.com/v1beta/models/text-embedding-004:embedContent?key={settings.gemini_api_key}", json={"content": {"parts": [{"text": text[:6000]}]}})
            return r.json()["embedding"]["values"]
    import hashlib
    h = hashlib.sha512(text.encode()).digest()
    return [((h[i % 64] / 255) - .5) for i in range(768)]
