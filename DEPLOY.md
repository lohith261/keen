# KEEN — Production Deployment Guide

**Frontend → Vercel** | **Backend → Fly.io**

Total time: ~15 minutes

---

## Prerequisites

- [flyctl](https://fly.io/docs/hands-on/install-flyctl/) — `brew install flyctl` (Mac) or `curl -L https://fly.io/install.sh | sh` (Linux)
- A [Vercel](https://vercel.com) account (free)
- A [Fly.io](https://fly.io) account (free — no credit card for hobby plan)

---

## Part 1 — Backend on Fly.io

### 1. Login and create the app

```bash
flyctl auth login

# From the repo root:
cd backend
fly launch --name keen-backend --region iad --no-deploy
# When prompted "Would you like to set up a Postgresql database?" → Yes
# When prompted "Would you like to set up an Upstash Redis database?" → Yes
# This creates both and links them automatically.
```

> `fly launch` reads `fly.toml` and sets up everything. It will print your app URL: `https://keen-backend.fly.dev`

### 2. Set secrets

```bash
# Run from the /backend directory.
# Paste each value after the = sign.

fly secrets set \
  SECRET_KEY="$(openssl rand -hex 32)" \
  CREDENTIAL_ENCRYPTION_KEY="your-32-byte-base64-key" \
  ANTHROPIC_API_KEY="sk-ant-..." \
  GEMINI_API_KEY="AIza..." \
  TINYFISH_API_KEY="tf-..."
```

> `DATABASE_URL` and `REDIS_URL` are set automatically by `fly launch` when you accept the Postgres and Redis prompts.

### 3. Deploy

```bash
# From /backend:
fly deploy
```

That's it. Fly builds your Docker image, pushes it, runs `alembic upgrade head`, and starts the server.

### 4. Verify

```bash
curl https://keen-backend.fly.dev/api/v1/health
# → {"status":"healthy","version":"0.1.0","environment":"production"}
```

---

## Part 2 — Frontend on Vercel

### 1. Import the repo

Go to [vercel.com/new](https://vercel.com/new) → Import your `keen` GitHub repo.

### 2. Configure the project

| Setting | Value |
|---|---|
| **Root Directory** | `frontend` |
| **Framework Preset** | Vite (auto-detected) |
| **Build Command** | `npm run build` |
| **Output Directory** | `dist` |

### 3. Add environment variable

| Key | Value |
|---|---|
| `VITE_API_URL` | `https://keen-backend.fly.dev` |

### 4. Deploy

Click **Deploy**. Your `keen-sigma.vercel.app` URL is now live and talking to the Fly.io backend.

---

## Part 3 — Update CORS on the backend

```bash
# From /backend — let the backend accept requests from your Vercel domain:
fly secrets set CORS_ORIGINS="https://keen-sigma.vercel.app,http://localhost:5173"
```

---

## Future deploys

Every time you push to `main` and want to redeploy:

```bash
# From /backend:
fly deploy
```

Or set up automatic deploys via Fly's GitHub integration:
```bash
fly ext github-actions
```

---

## Local development (unchanged)

```bash
# Start all services with Docker Compose:
docker compose up

# Or run individually:
cd backend && uvicorn app.main:app --reload --port 8000
cd frontend && npm run dev
```

No `VITE_API_URL` needed locally — the Vite proxy handles it.

---

## Architecture

```
Browser (Vercel — keen-sigma.vercel.app)
    │
    ├── REST:      VITE_API_URL/api/v1/*   ──► Fly.io (FastAPI)
    │                                              │
    └── WebSocket: wss://VITE_API_URL/ws/*         ├── Fly Postgres
                                                   ├── Upstash Redis
                                                   └── TinyFish (browser automation)
```

---

## Secrets reference

| Secret | Description |
|---|---|
| `DATABASE_URL` | Auto-set by Fly Postgres |
| `REDIS_URL` | Auto-set by Upstash Redis |
| `SECRET_KEY` | JWT signing key |
| `CREDENTIAL_ENCRYPTION_KEY` | AES-256-GCM vault key (32-byte base64) |
| `ANTHROPIC_API_KEY` | Claude (primary LLM) |
| `GEMINI_API_KEY` | Gemini (fallback LLM) |
| `TINYFISH_API_KEY` | TinyFish browser automation |
| `CORS_ORIGINS` | Comma-separated allowed origins |
