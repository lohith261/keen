# KEEN — Op/Intelligence

**Sharper Judgment. Faster Execution.**

KEEN is a multi-agent AI system that automates the data gathering and reporting layer of private equity due diligence. Three specialised agents — Research, Analysis, and Delivery — extract data from live enterprise sources, cross-reference findings, and produce a structured PDF + Excel report delivered automatically to Slack, email, Google Drive, or SharePoint.

> **Status:** Early access · Built at [TinyFish Accelerator](https://www.tinyfish.ai/accelerator) (2026 cohort)
>
> 🌐 **Live:** [keen-sigma.vercel.app](https://keen-sigma.vercel.app) · Backend: [keen-backend.fly.dev](https://keen-backend.fly.dev/api/v1/health)

---

## What's Actually Built

| Component | Status | Notes |
|---|---|---|
| 3-agent pipeline (Research → Analysis → Delivery) | ✅ Production | Step-based, checkpointed, resume-safe |
| Demo mode with Zendesk Inc fixture dataset | ✅ Complete | Auto-starts on first dashboard load, 16 fixture files, 8 baked-in discrepancies |
| 5 REST API integrations (live) | ✅ Complete | Salesforce, NetSuite, SEC EDGAR, HubSpot, Crunchbase |
| Browser-automation connectors (via TinyFish) | ✅ Architecture | Delegated to TinyFish API — needs `TINYFISH_API_KEY` |
| PDF + Excel report export | ✅ Production | `/export/pdf`, `/export/excel` endpoints |
| Distribution: Slack, Email, Google Drive, SharePoint | ✅ Production | Auto-delivered on pipeline completion |
| Document ingestion pipeline | ✅ Production | PDF, Excel, PowerPoint, Word, CSV upload — text extracted and included in analysis |
| AES-256-GCM credential vault | ✅ Production | Per-engagement, per-user isolated |
| Supabase authentication (login / signup) | ✅ Production | JWT ES256, per-user data isolation |
| Real-time WebSocket pipeline monitoring | ✅ Production | Live agent step progress in browser |
| Multi-LLM (Claude → Gemini → Groq fallback) | ✅ Production | Never breaks if one provider is down |
| SEC EDGAR company autocomplete | ✅ Production | Debounced live lookup in New Engagement modal |
| Engagement search + status filter | ✅ Production | Client-side filter on company name / PE firm + status chips |
| Deal Brief one-pager view | ✅ Production | Compact summary tab in Results panel — recommendation + severity counts + top criticals |
| Data appendix (charts/tables in report) | 🔲 Stub | Returns `pending_integration` |
| Financial model sync | 🔲 Stub | Returns `pending_integration` |
| Billing / pricing layer | 🔲 Not built | |
| Admin dashboard | 🔲 Not built | |

---

## 🚀 Try the Demo (5 minutes)

No credentials or account required to run the demo.

**URL:** [keen-sigma.vercel.app](https://keen-sigma.vercel.app)

### Step 1 — Check system status

Click **STATUS** in the nav bar. A green **OPERATIONAL** badge means the backend, database, and LLM are healthy and ready.

### Step 2 — Confirm Demo mode is active

Look for the **amber flask pill** labelled `DEMO` in the top nav. If it shows `LIVE`, click it once to switch back. Demo mode uses the Zendesk Inc fixture dataset — no credentials needed.

### Step 3 — Open the Dashboard

Click **DASHBOARD** in the nav (no login required in Demo mode). The dashboard auto-creates a Zendesk Inc engagement on first load and starts the pipeline immediately.

### Step 4 — Watch the pipeline run

Three agents execute in sequence:

```
Research Agent  →  Analysis Agent  →  Delivery Agent
```

Each agent shows real-time step progress via WebSocket. The Research Agent processes simulated CRM, ERP, market, and document sources.

### Step 5 — Create your own engagement (optional)

Click **+ New Engagement** and start typing a company name. The modal fetches live suggestions from SEC EDGAR as you type. Fill in:

| Field | Suggested value |
|---|---|
| **Target Company** | Start typing — EDGAR autocomplete appears |
| **PE Firm** | Your firm name (optional) |
| **Deal Size** | e.g. `$50M` (optional) |
| **Engagement Type** | `Full Due Diligence` |

Click **START PIPELINE →**. The engagement is created and the orchestrator starts immediately.

### Step 6 — Upload documents

Once an engagement is open, click the **DOCUMENTS** tab. Drag and drop PDF, Excel, PowerPoint, Word, or CSV files — they are extracted and injected into the analysis pipeline.

### Step 7 — Review findings

Once the pipeline completes, click the **RESULTS** tab. Findings are sorted by severity:

| Finding | Sources | Gap |
|---|---|---|
| Revenue gap | Salesforce vs NetSuite | ~$1.3M |
| Funnel leakage | HubSpot vs Salesforce | 7% vs 15–20% benchmark |
| R&D cost mismatch | SAP vs Oracle GL | ~$400K |
| Funding discrepancy | Crunchbase vs SEC proxy | ~$500K |
| Headcount mismatch | ZoomInfo / SAP / LinkedIn | 11–25 person gap |
| SMB churn | Dynamics | 18.4% (above benchmark) |
| Overdue AR | Oracle | 2 accounts 120+ days |
| Key person risk | Sales Navigator | VP Engineering departed Feb 2026 |

Toggle **BRIEF** in the top bar for a compact one-page Deal Brief — recommendation badge, severity counts, and top criticals — useful for sending to a partner before a full review.

### Step 8 — Export the report

Use the **PDF** and **XLSX** buttons in the Results panel to download the executive report and financial workbook. The **SHEETS** and **DRIVE** buttons push directly to Google Sheets / Drive.

---

## 🤖 How It Works

### Research Agent

Plans which sources to query (using Claude) based on engagement type and company profile, then authenticates and extracts from each configured source.

**5 live REST integrations:**

| System | Auth | Data Extracted |
|---|---|---|
| **Salesforce** | OAuth 2.0 + refresh token | CRM pipeline, deal history, contact records, activity logs |
| **NetSuite** | OAuth 1.0 TBA (HMAC-SHA256) | Revenue data, expense records, journal entries, balance sheet |
| **SEC EDGAR** | Public API (no auth) | 10-K/Q filings, insider transactions, proxy statements |
| **HubSpot** | API Key | Marketing metrics, lead funnel, campaign ROI |
| **Crunchbase** | API Key | Funding history, acquisitions, key people |

**Browser-automation sources (via TinyFish):**

Bloomberg Terminal · Capital IQ · PitchBook · LinkedIn Sales Navigator · SAP Fiori · Oracle Fusion · Microsoft Dynamics · QuickBooks · ZoomInfo · Marketo

These connectors send natural-language goals to the TinyFish Web Agent API, which handles navigation and extraction. Requires `TINYFISH_API_KEY`.

**Document ingestion:**

Uploaded documents (PDF, Excel, PowerPoint, Word, CSV) are text-extracted using `pdfplumber`, `python-pptx`, and `openpyxl`, then injected as a source into the Research Agent output.

### Analysis Agent

Receives the Research Agent's compiled output and performs:

- **Revenue variance detection** — CRM pipeline vs ERP actuals, flags gaps > 5%
- **Cost variance analysis** — expense cross-referencing, flags gaps > 8%
- **Customer metrics** — churn, LTV, CAC, NRR derived from CRM + billing data
- **LLM cross-referencing** — Claude matches entities across sources and surfaces discrepancies
- **Confidence scoring** — reliability and impact scores assigned to every finding
- **Exception routing** — `critical` severity findings flagged for human review

### Delivery Agent

- Generates executive summary (LLM-drafted narrative)
- Generates full 9-section due diligence report (batched, checkpoint-safe)
- Runs PII compliance sweep before distribution
- Distributes to configured channels (Slack / email / Google Drive / SharePoint)
- Writes full audit trail (timestamp, source, agent step per data point)

---

## 🏗️ Tech Stack

### Frontend

| Layer | Technology |
|---|---|
| Framework | React 18 + TypeScript |
| Build | Vite 5 |
| Styling | Tailwind CSS 3 + CSS custom properties (dark/light themes) |
| 3D / WebGL | Three.js — interactive particle background (custom GLSL shaders) |
| Animations | GSAP — scroll reveals, text parallax, count-up |
| Auth | Supabase JS SDK — `onAuthStateChange`, JWT stored in localStorage |
| Icons | Lucide React |
| Markdown | react-markdown — structured finding descriptions and executive summaries |

### Backend

| Layer | Technology |
|---|---|
| Framework | FastAPI (Python 3.11+) |
| Database | Supabase (managed PostgreSQL) via SQLAlchemy 2.0 async |
| Migrations | Alembic (5 migrations) |
| Checkpointing | Redis (fast, 24h TTL) + PostgreSQL (durable) |
| Real-time | WebSocket (FastAPI native) — live agent status & progress |
| Auth | Supabase JWT — ES256 JWKS verification, `get_current_user` FastAPI dep |
| Encryption | AES-256-GCM credential vault (`cryptography` library) |
| LLM | Claude (primary) → Gemini → Groq (automatic fallback chain) |
| Document parsing | pdfplumber (PDF) · python-pptx (PowerPoint) · openpyxl (Excel) |
| Browser automation | TinyFish Web Agent API (SSE streaming, natural-language goals) |
| HTTP client | httpx (async) |
| Testing | pytest + pytest-asyncio (20 tests) |

### Deployment

| Service | Platform |
|---|---|
| Frontend | Vercel (auto-deploy from `main`) |
| Backend | Fly.io (rolling deploy, health checks) |
| Database | Supabase managed PostgreSQL |
| Cache | Redis (Fly.io managed) |

---

## 🧩 Project Structure

```
keen/
├── frontend/
│   └── src/
│       ├── App.tsx                       # Landing page — all sections & data
│       ├── main.tsx                      # Root — AuthProvider, ThemeProvider
│       ├── components/
│       │   ├── auth/
│       │   │   ├── AuthModal.tsx         # Inline sign-in / sign-up modal
│       │   │   └── AuthPage.tsx          # Standalone auth page (fallback)
│       │   ├── dashboard/
│       │   │   ├── Dashboard.tsx         # Engagement list + search/filter + stats bar
│       │   │   ├── PipelineView.tsx      # Real-time agent progress + WS
│       │   │   ├── ResultsPanel.tsx      # Findings + Deal Brief + export buttons
│       │   │   ├── DocumentsPanel.tsx    # Document upload, drag-and-drop, status
│       │   │   ├── NewEngagementModal.tsx # Create engagement + EDGAR autocomplete
│       │   │   └── CredentialsModal.tsx  # Per-source credential entry
│       │   ├── ui/
│       │   │   └── Toast.tsx             # Toast notification system
│       │   ├── RequestAccessModal.tsx    # "Book a Demo" form
│       │   ├── WebGLBackground.tsx       # Three.js particle background
│       │   └── ...scroll, parallax, GSAP components
│       ├── context/
│       │   ├── AuthContext.tsx           # Supabase session + signIn/signUp/signOut
│       │   ├── ThemeContext.tsx
│       │   ├── DemoModeContext.tsx
│       │   └── ViewContext.tsx
│       ├── hooks/
│       │   ├── useScrollProgress.ts
│       │   └── useSystemHealth.ts        # Health check polling
│       └── lib/
│           └── apiClient.ts              # Typed API client + credential specs
│
└── backend/
    └── app/
        ├── main.py                       # FastAPI entry point, CORS, routers
        ├── config.py                     # Pydantic settings (env vars)
        ├── database.py                   # Async SQLAlchemy engine
        ├── models/                       # ORM models (7 tables incl. documents)
        ├── schemas/                      # Pydantic schemas
        ├── api/
        │   ├── engagements.py            # Core CRUD + orchestration endpoints
        │   ├── documents.py              # File upload, list, delete endpoints
        │   ├── health.py                 # /health, /health/ready, /health/llm
        │   ├── leads.py                  # Demo request / book-a-demo capture
        │   └── auth_deps.py              # JWT verification, get_current_user
        ├── services/
        │   └── document_processor.py     # pdfplumber / python-pptx / openpyxl extraction
        ├── websocket/                    # Real-time agent event broadcasting
        ├── agents/
        │   ├── base.py                   # BaseAgent + step execution + checkpointing
        │   ├── orchestrator.py           # Research → Analysis → Delivery pipeline
        │   ├── research.py               # Data extraction (demo + live + documents)
        │   ├── analysis.py               # Cross-referencing & variance detection
        │   └── delivery.py               # Report generation & distribution
        ├── llm/
        │   ├── client.py                 # Claude → Gemini → Groq fallback chain
        │   ├── prompts.py                # All prompt templates
        │   └── exceptions.py
        ├── integrations/
        │   ├── demo/                     # 16 JSON fixture files (Zendesk Inc)
        │   ├── live/                     # Salesforce, NetSuite, SEC EDGAR, HubSpot, Crunchbase
        │   ├── browser/                  # TinyFish connector base + goal builders
        │   └── distribution/             # Slack, Email, Google Drive, SharePoint
        └── auth/
            ├── vault.py                  # AES-256-GCM credential encryption
            └── manager.py                # Auth dispatch (OAuth, API key, TinyFish)
```

---

## ⚙️ Agent Infrastructure

All three agents extend `BaseAgent`, which provides:

- **Step-based execution** — each agent defines an ordered list of named steps. Steps execute sequentially and emit structured findings.
- **Checkpointing** — state persisted to Redis (fast, 24h TTL) and PostgreSQL (durable) every 90 seconds. Resume picks up from the next uncompleted step.
- **Pause & resume** — `stop()` signals the agent to checkpoint after the current step. The orchestrator propagates the signal across the pipeline.
- **Structured findings** — steps emit `Finding` records (type, severity, source, `requires_human_review` flag) persisted to DB and streamed via WebSocket.
- **Real-time progress** — every step transition emits an event via the `on_progress` callback, broadcast to connected clients over WebSocket.

---

## 🔐 Authentication & Security

### User Auth (Supabase)

- Sign up / sign in via Supabase JS SDK
- Backend verifies JWT using JWKS endpoint (`/auth/v1/.well-known/jwks.json`), ES256 keys
- `get_current_user` FastAPI dependency — 401 on missing/invalid token
- Per-user data isolation: engagements stamped with `user_id`, filtered on every list query

### Credential Vault

- API keys and OAuth tokens encrypted with AES-256-GCM before storage
- Encryption key loaded from `CREDENTIAL_ENCRYPTION_KEY` env var (stable across deploys)
- Per-engagement scope — credentials never cross engagement or user boundaries

### Data Privacy

- No training on customer data
- Full audit trail per engagement (timestamp, source, agent step per data point)
- PII compliance sweep run by Delivery Agent before any distribution

---

## 🤖 LLM Integration

Multi-provider fallback chain — the pipeline never breaks if one provider is unavailable:

```
Request → Claude (primary) → Gemini (fallback) → Groq (fallback) → deterministic stub
```

| Agent | Step | LLM Role |
|---|---|---|
| Research | `plan_extraction` | Prioritise data sources for this engagement |
| Analysis | `cross_reference_sources` | Match entities, surface discrepancies |
| Analysis | `score_findings` | Assign reliability and impact scores |
| Delivery | `generate_executive_summary` | Board-ready one-page narrative |
| Delivery | `generate_detailed_report` | Full 9-section DD report (batched, checkpointed) |

---

## 🧪 Demo Mode vs Live Mode

| | Demo Mode | Live Mode |
|---|---|---|
| Toggle | Amber flask pill `DEMO` | Green pulsing pill `LIVE` |
| Data | JSON fixture files (Zendesk Inc) | Live enterprise connectors |
| Credentials required | None | OAuth / API keys per source |
| Pipeline config | `demo_mode: true` | `demo_mode: false` |
| TinyFish calls | Fixture data returned | Real browser automation |
| Auto-start | Creates Zendesk engagement on first load | Manual — click + New Engagement |

---

## 🌐 API Reference

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `GET` | `/api/v1/health` | None | Service health |
| `GET` | `/api/v1/health/ready` | None | DB + Redis readiness |
| `GET` | `/api/v1/health/llm` | None | LLM provider status |
| `POST` | `/api/v1/leads` | None | Book-a-demo form capture |
| `POST` | `/api/v1/engagements` | JWT | Create engagement |
| `GET` | `/api/v1/engagements` | JWT | List user's engagements |
| `GET` | `/api/v1/engagements/{id}` | JWT | Get engagement + agent runs |
| `DELETE` | `/api/v1/engagements/{id}` | JWT | Delete engagement |
| `POST` | `/api/v1/engagements/{id}/start` | JWT | Start orchestration |
| `POST` | `/api/v1/engagements/{id}/pause` | JWT | Pause + checkpoint |
| `POST` | `/api/v1/engagements/{id}/resume` | JWT | Resume from checkpoint |
| `GET` | `/api/v1/engagements/{id}/findings` | JWT | Get all findings |
| `GET` | `/api/v1/engagements/{id}/documents` | JWT | List uploaded documents |
| `POST` | `/api/v1/engagements/{id}/documents` | JWT | Upload document (multipart) |
| `DELETE` | `/api/v1/engagements/{id}/documents/{doc_id}` | JWT | Delete document |
| `GET` | `/api/v1/engagements/{id}/export/pdf` | JWT | Download PDF report |
| `GET` | `/api/v1/engagements/{id}/export/excel` | JWT | Download Excel workbook |
| `GET` | `/api/v1/engagements/{id}/export/sheets` | JWT | Push to Google Sheets |
| `GET` | `/api/v1/engagements/{id}/export/drive` | JWT | Upload to Google Drive |
| `WS` | `/ws/agent-status` | None | Real-time agent events |

---

## ⚙️ Environment Variables

### Required (backend)

| Variable | Description |
|---|---|
| `DATABASE_URL` | PostgreSQL connection string (`postgresql+asyncpg://...`) |
| `REDIS_URL` | Redis connection string |
| `SECRET_KEY` | App secret key |
| `CREDENTIAL_ENCRYPTION_KEY` | 32-byte base64 AES-256 key for credential vault |
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_ANON_KEY` | Supabase anonymous (public) key |
| `CORS_ORIGINS` | Comma-separated allowed origins |

### LLM Keys (at least one required)

| Variable | Provider | Role |
|---|---|---|
| `ANTHROPIC_API_KEY` | Claude | Primary LLM |
| `GEMINI_API_KEY` | Gemini | First fallback |
| `OPENAI_API_KEY` | GPT-4 | Second fallback |
| `GROQ_API_KEY` | Groq | Third fallback |

### Integration Keys (optional — only needed for live mode)

| Variable | Used For |
|---|---|
| `TINYFISH_API_KEY` | Browser automation (Bloomberg, CapIQ, PitchBook, SAP, Oracle, Dynamics, Sales Navigator, ZoomInfo, QuickBooks, Marketo) |

### Required (frontend)

| Variable | Description |
|---|---|
| `VITE_API_URL` | Backend base URL (e.g. `https://keen-backend.fly.dev`) |
| `VITE_SUPABASE_URL` | Supabase project URL |
| `VITE_SUPABASE_ANON_KEY` | Supabase anonymous key |

---

## 🛠️ Local Development

### Prerequisites

- Node.js ≥ 18, npm ≥ 9
- Python ≥ 3.11
- Redis
- Supabase project (free tier works)

### Frontend

```bash
cd frontend
npm install
cp .env.example .env.local    # add VITE_SUPABASE_URL, VITE_SUPABASE_ANON_KEY
npm run dev                    # → http://localhost:5173
```

### Backend

```bash
cd backend

python3 -m venv .venv
source .venv/bin/activate

pip install -e ".[dev]"

cp .env.example .env
# Fill in: DATABASE_URL, REDIS_URL, SECRET_KEY, CREDENTIAL_ENCRYPTION_KEY,
#          SUPABASE_URL, SUPABASE_ANON_KEY, at least one LLM key

alembic upgrade head

uvicorn app.main:app --reload --port 8000
```

Vite proxies `/api/*` and `/ws/*` to `localhost:8000` automatically.

### Generate a CREDENTIAL_ENCRYPTION_KEY

```bash
python3 -c "import base64, os; print(base64.b64encode(os.urandom(32)).decode())"
```

### Other Commands

```bash
# Frontend
npm run build        # Production build
npm run lint         # ESLint

# Backend
pytest tests/ -v     # Run test suite
ruff check app/      # Python lint
```

---

## 📦 Deployment

### Frontend → Vercel

```bash
cd frontend
npm run build        # → frontend/dist/
```

Connect the repo to Vercel. Set `VITE_API_URL`, `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY` in Vercel environment variables.

### Backend → Fly.io

```bash
cd backend
flyctl deploy --strategy rolling
```

Set all backend secrets via:

```bash
flyctl secrets set ANTHROPIC_API_KEY=sk-ant-... TINYFISH_API_KEY=sk-tinyfish-... ...
```

---

## 📋 License

© 2026 KEEN — Backed by [TinyFish Accelerator](https://www.tinyfish.ai/accelerator)
