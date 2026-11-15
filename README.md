# LinkSentinel
AI URL shortener + RAG analytics. Built by Nikhil Chary Sriramoju (github.com/Nikhil-creat).
```
cp .env.example .env   # add GROQ_API_KEY or GEMINI_API_KEY (model auto-detected)
docker compose up --build
```
Web: http://localhost:8080 · API docs: http://localhost:8000/docs
Frontend alone works on GitHub Pages (`frontend/`); paste a free Groq/Gemini key in the chat panel.

Tables + pgvector extension are created on API startup. Register: POST /api/v1/auth/register, login at /api/v1/auth/login, then use the Bearer token on /api/v1/analytics/chat.
Promote an admin: `docker compose exec db psql -U ls -c "update users set role='admin' where email='you@x.com'"`.

## Deploy backend on Render (free)
Render dashboard → New → Blueprint → pick this repo (uses `render.yaml`). Free accounts allow one Key Value instance, so paste an existing Render Key Value internal URL (or a free Upstash `rediss://` URL) into `REDIS_URL`. Set `GEMINI_API_KEY` (or `GROQ_API_KEY`) and `CORS_ORIGINS=https://YOUR-APP.vercel.app`. Then put the API URL in `frontend/config.js`.
Free tier sleeps after idle, so the first request is slow. Agents run inline (`INLINE_AGENTS=true`) because there is no free Celery worker.

## Ops
`docker compose up` also starts Prometheus (:9090) and Grafana (:3000, add Prometheus at http://prometheus:9090). Metrics: `/metrics`.
Migrations: `docker compose exec api alembic upgrade head`. CNN: add screenshots to `data/safe` and `data/spoof`, `pip install -r requirements-cnn.txt`, run `python scripts/train_cnn.py`.

## Frontend (Vercel) — SEO build
`frontend/` is a static multi-page site: `/`, `/threat-shield`, `/console`, `/security`, `/roadmap`, `/about`, plus `404.html`, `sitemap.xml`, `robots.txt`, `llms.txt`, favicon set and social image.
`frontend/build.mjs` runs on Vercel (`vercel.json` sets it) and writes `dist/` with the real URLs stamped in.
Vercel → Project → Settings → Environment Variables:
- `SITE_URL` — your final address, e.g. `https://yourdomain.com` (no trailing slash). Falls back to the Vercel production URL if unset.
- `API_URL` — your Render API URL (no trailing slash). Until set, the site runs in demo mode and says so.
Project Settings → General → Root Directory must be `frontend`; Framework Preset `Other`; leave Build/Output overrides empty (they come from `vercel.json`).
Custom domain: Settings → Domains → Add, copy the DNS records to your registrar, then set `SITE_URL` and redeploy. Also add the domain to `CORS_ORIGINS` on Render.
