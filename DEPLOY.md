# KEEN — Production Deployment Guide

**Frontend → Vercel** | **Backend → Google Cloud Run**

---

## Prerequisites

- [Google Cloud CLI](https://cloud.google.com/sdk/docs/install) (`gcloud`)
- [Vercel CLI](https://vercel.com/docs/cli) (`npm i -g vercel`) — or use the Vercel dashboard
- A GCP project with billing enabled
- A Supabase project (PostgreSQL)
- An Upstash Redis instance (free tier at [upstash.com](https://upstash.com))

---

## Part 1 — Backend on Google Cloud Run

### 1. Set up GCP project

```bash
# Authenticate
gcloud auth login

# Set your project
export PROJECT_ID=your-gcp-project-id
gcloud config set project $PROJECT_ID

# Enable required APIs
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  secretmanager.googleapis.com \
  containerregistry.googleapis.com
```

### 2. Store secrets in Secret Manager

```bash
# Run each command and paste the value when prompted (Ctrl+D to save)

echo -n "postgresql+asyncpg://user:pass@host/db" | gcloud secrets create KEEN_DATABASE_URL --data-file=-
echo -n "rediss://default:token@host:port" | gcloud secrets create KEEN_REDIS_URL --data-file=-
echo -n "$(openssl rand -hex 32)" | gcloud secrets create KEEN_SECRET_KEY --data-file=-
echo -n "your-32-byte-base64-key" | gcloud secrets create KEEN_CREDENTIAL_ENCRYPTION_KEY --data-file=-
echo -n "sk-ant-..." | gcloud secrets create KEEN_ANTHROPIC_API_KEY --data-file=-
echo -n "AIza..." | gcloud secrets create KEEN_GEMINI_API_KEY --data-file=-
echo -n "tf-..." | gcloud secrets create KEEN_TINYFISH_API_KEY --data-file=-
```

### 3. Grant Cloud Run access to secrets

```bash
# Get the Cloud Run service account email
export SA=$(gcloud iam service-accounts list --filter="displayName:Compute Engine default" --format="value(email)")

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SA" \
  --role="roles/secretmanager.secretAccessor"
```

### 4. Build and deploy manually (first time)

```bash
# From the repo root:
docker build -f Dockerfile.backend -t gcr.io/$PROJECT_ID/keen-backend .
docker push gcr.io/$PROJECT_ID/keen-backend

gcloud run deploy keen-backend \
  --image=gcr.io/$PROJECT_ID/keen-backend \
  --region=us-central1 \
  --platform=managed \
  --allow-unauthenticated \
  --port=8080 \
  --memory=512Mi \
  --cpu=1 \
  --timeout=3600 \
  --min-instances=0 \
  --max-instances=3 \
  --set-secrets=DATABASE_URL=KEEN_DATABASE_URL:latest,REDIS_URL=KEEN_REDIS_URL:latest,SECRET_KEY=KEEN_SECRET_KEY:latest,CREDENTIAL_ENCRYPTION_KEY=KEEN_CREDENTIAL_ENCRYPTION_KEY:latest,ANTHROPIC_API_KEY=KEEN_ANTHROPIC_API_KEY:latest,GEMINI_API_KEY=KEEN_GEMINI_API_KEY:latest,TINYFISH_API_KEY=KEEN_TINYFISH_API_KEY:latest \
  --set-env-vars=ENVIRONMENT=production,DEBUG=false
```

> Cloud Run will print your service URL, e.g. `https://keen-backend-xxxx.run.app`

### 5. Set CORS to allow Vercel frontend

```bash
export BACKEND_URL=https://keen-backend-xxxx.run.app   # your Cloud Run URL

gcloud run services update keen-backend \
  --region=us-central1 \
  --update-env-vars=CORS_ORIGINS=https://keen-sigma.vercel.app,http://localhost:5173
```

### 6. (Optional) Auto-deploy on push with Cloud Build

```bash
# Connect your GitHub repo in Cloud Build triggers:
# GCP Console → Cloud Build → Triggers → Connect Repository
# Then create a trigger:
#   - Event: Push to main branch
#   - Config: cloudbuild.yaml (at repo root)
#   - Substitutions: _PROJECT_ID, _REGION=us-central1, _SERVICE_NAME=keen-backend
```

---

## Part 2 — Frontend on Vercel

### 1. Import the repo

Go to [vercel.com/new](https://vercel.com/new) → Import your `keen` GitHub repo.

### 2. Configure the project

| Setting | Value |
|---|---|
| **Root Directory** | `frontend` |
| **Framework Preset** | Vite |
| **Build Command** | `npm run build` |
| **Output Directory** | `dist` |

### 3. Add environment variable

| Key | Value |
|---|---|
| `VITE_API_URL` | `https://keen-backend-xxxx.run.app` |

> Replace with your actual Cloud Run URL from Part 1 Step 4.

### 4. Deploy

Click **Deploy**. Your existing `keen-sigma.vercel.app` domain will automatically use the new build.

---

## Part 3 — Verify deployment

```bash
# Health check
curl https://keen-backend-xxxx.run.app/api/v1/health

# Expected:
# {"status":"healthy","version":"0.1.0","environment":"production"}
```

Then open `https://keen-sigma.vercel.app` → click **DASHBOARD** → create a demo engagement → watch the pipeline run live.

---

## Local development (unchanged)

```bash
# Backend
cd backend && uvicorn app.main:app --reload --port 8000

# Frontend (proxies /api and /ws to localhost:8000 via vite.config.ts)
cd frontend && npm run dev
```

No `VITE_API_URL` needed locally — the Vite proxy handles it.

---

## Architecture diagram

```
Browser (Vercel)
    │
    ├── REST: VITE_API_URL/api/v1/*  ─────────────────────────► Cloud Run (FastAPI)
    │                                                               │
    └── WebSocket: wss://VITE_API_URL/ws/agent-status              ├── Supabase (PostgreSQL)
                                                                    ├── Upstash (Redis)
                                                                    └── TinyFish (browser automation)
```

---

## Secrets reference

| Secret Manager key | Maps to env var | Description |
|---|---|---|
| `KEEN_DATABASE_URL` | `DATABASE_URL` | Supabase PostgreSQL async URL |
| `KEEN_REDIS_URL` | `REDIS_URL` | Upstash Redis URL (`rediss://...`) |
| `KEEN_SECRET_KEY` | `SECRET_KEY` | JWT signing key (64 hex chars) |
| `KEEN_CREDENTIAL_ENCRYPTION_KEY` | `CREDENTIAL_ENCRYPTION_KEY` | AES-256-GCM vault key |
| `KEEN_ANTHROPIC_API_KEY` | `ANTHROPIC_API_KEY` | Claude (primary LLM) |
| `KEEN_GEMINI_API_KEY` | `GEMINI_API_KEY` | Gemini (fallback LLM) |
| `KEEN_TINYFISH_API_KEY` | `TINYFISH_API_KEY` | TinyFish browser automation |
