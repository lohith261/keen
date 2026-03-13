# KEEN

**Sharper Judgment. Faster Execution.**

KEEN is a multi-agent operational intelligence platform that replicates McKinsey-grade private equity due diligence — compressing **4 weeks of work into 4 hours** through autonomous execution across live enterprise systems.

Built as part of the **TinyFish Accelerator (2026)**.

---

## ✨ Highlights

| Metric | Value |
|---|---|
| **Time compression** | 4 weeks → 4 hours (98% reduction) |
| **Cost efficiency** | $200K → $40K (80% savings) |
| **System access** | 15+ live enterprise sources |
| **Accuracy rate** | 99.7% validated output |

---

## 🏗️ Tech Stack

### Frontend

| Layer | Technology |
|---|---|
| **Framework** | [React 18](https://react.dev/) + [TypeScript](https://www.typescriptlang.org/) |
| **Build tool** | [Vite 5](https://vitejs.dev/) |
| **Styling** | [Tailwind CSS 3](https://tailwindcss.com/) + CSS custom properties (dark/light themes) |
| **3D / WebGL** | [Three.js](https://threejs.org/) — interactive particle background with custom GLSL shaders |
| **Animations** | [GSAP](https://gsap.com/) — scroll reveals, text reveals, parallax, count-up counters |
| **Icons** | [Lucide React](https://lucide.dev/) |

### Backend

| Layer | Technology |
|---|---|
| **Framework** | [FastAPI](https://fastapi.tiangolo.com/) (Python 3.11+) |
| **Database** | [Supabase](https://supabase.com/) (managed PostgreSQL) via [SQLAlchemy 2.0](https://www.sqlalchemy.org/) async |
| **Migrations** | [Alembic](https://alembic.sqlalchemy.org/) |
| **Task queue** | [Celery](https://docs.celeryq.dev/) + [Redis](https://redis.io/) |
| **Real-time** | WebSocket (FastAPI native) — live agent status & progress |
| **Auth** | Dynamic auth manager (OAuth, SSO, MFA, API key, browser/TinyFish) |
| **Encryption** | AES-256-GCM credential vault via [cryptography](https://cryptography.io/) |
| **Testing** | [pytest](https://pytest.org/) + pytest-asyncio |

---

## 🧩 Project Structure

```
keen/
├── frontend/                         # React + Vite + Tailwind
│   ├── index.html                    # HTML entry point
│   ├── package.json                  # Node dependencies & scripts
│   ├── vite.config.ts                # Vite config with backend proxy
│   ├── tsconfig.json                 # TypeScript config
│   ├── eslint.config.js              # ESLint config
│   ├── tailwind.config.js            # Tailwind CSS config
│   ├── postcss.config.js             # PostCSS config
│   └── src/
│       ├── App.tsx                   # Main application — all sections & data
│       ├── main.tsx                  # React entry point with ThemeProvider
│       ├── index.css                 # Design tokens, animations, themes
│       ├── lib/
│       │   ├── apiClient.ts          # Typed REST + WebSocket client
│       │   └── supabaseClient.ts     # Supabase JS client
│       ├── components/
│       │   ├── WebGLBackground.tsx   # Three.js particle field
│       │   ├── ScrollReveal.tsx      # Scroll animations
│       │   ├── TextReveal.tsx        # Text animation
│       │   ├── ParallaxSection.tsx   # Parallax wrapper
│       │   ├── CountUp.tsx           # Animated counter
│       │   ├── MagneticElement.tsx   # Magnetic hover effect
│       │   ├── ScrollProgressBar.tsx # Scroll progress indicator
│       │   ├── ScrollIndicator.tsx   # Scroll-down hint
│       │   ├── ThemeToggle.tsx       # Dark/light theme switch
│       │   ├── Loader.tsx            # Loading screen
│       │   ├── SmoothScroll.tsx      # Smooth scroll utility
│       │   └── HorizontalScroll.tsx  # Horizontal scroll section
│       ├── context/
│       │   └── ThemeContext.tsx       # Theme state context
│       ├── hooks/
│       │   └── useScrollProgress.ts  # Scroll & mouse hooks
│       └── shaders/
│           └── background.ts         # GLSL shaders for WebGL
│
├── backend/                          # Python + FastAPI
│   ├── pyproject.toml                # Python dependencies & config
│   ├── alembic.ini                   # Alembic migration config
│   ├── .env.example                  # Environment variable template
│   ├── app/
│   │   ├── main.py                   # FastAPI entry point
│   │   ├── config.py                 # Pydantic settings
│   │   ├── database.py               # Async SQLAlchemy engine
│   │   ├── dependencies.py           # FastAPI DI
│   │   ├── models/                   # ORM models (6 tables)
│   │   ├── schemas/                  # Pydantic schemas
│   │   ├── api/                      # REST endpoints (/api/v1)
│   │   ├── websocket/                # Real-time agent events
│   │   ├── agents/                   # Multi-agent orchestration
│   │   │   ├── base.py               # Abstract agent + checkpointing
│   │   │   ├── orchestrator.py       # Research → Analysis → Delivery
│   │   │   ├── research.py           # Data extraction (15+ sources)
│   │   │   ├── analysis.py           # Cross-referencing & variance
│   │   │   └── delivery.py           # Report generation
│   │   ├── auth/                     # Auth manager + credential vault
│   │   ├── integrations/             # Enterprise connectors
│   │   └── services/                 # Business logic
│   ├── alembic/                      # Database migrations
│   └── tests/                        # pytest suite (20 tests)
│
├── README.md                         # This file
└── .gitignore                        # Unified gitignore
```

---

## 📄 Page Sections

1. **Hero** — Full-screen intro with animated text reveal, WebGL particle background, and CTA buttons
2. **Performance Metrics** — Animated count-up statistics (time, cost, access, accuracy)
3. **Agent Architecture** — Three autonomous agents: *Research*, *Analysis*, *Delivery* — each with live status indicators
4. **Operational Capabilities** — Stateful execution, dynamic authentication, multi-agent coordination, browser orchestration
5. **Enterprise Integrations** — 15+ connected systems (Salesforce, NetSuite, SAP, Bloomberg, SEC EDGAR, etc.)
6. **Competitive Advantage** — 19–27 month technical moat positioning, target market, ROI breakdown

---

## 🚀 Getting Started

### Prerequisites

- **Node.js** ≥ 18, **npm** ≥ 9
- **Python** ≥ 3.11
- **Redis** (for agent checkpointing)
- **Supabase** project (managed PostgreSQL)

### Frontend

```bash
cd frontend
npm install
npm run dev          # → http://localhost:5173
```

### Backend

```bash
cd backend

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -e ".[dev]"

# Configure environment
cp .env.example .env
# → Fill in Supabase URL, keys, Redis URL, encryption key, etc.

# Run database migration
alembic upgrade head

# Start the API server
uvicorn app.main:app --reload --port 8000
```

The Vite dev server automatically proxies `/api/*` and `/ws/*` to the backend at `localhost:8000`.

### Other Commands

```bash
# Frontend (from frontend/)
npm run build        # Production build
npm run preview      # Preview production build
npm run lint         # Run ESLint

# Backend (from backend/)
pytest tests/ -v     # Run test suite (20 tests)
ruff check app/      # Lint Python code
```

---

## 🔌 API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/health` | Service health check |
| `GET` | `/api/v1/health/ready` | Readiness check (DB + Redis) |
| `POST` | `/api/v1/leads` | Submit "Request Access" form |
| `GET` | `/api/v1/leads` | List all leads |
| `POST` | `/api/v1/engagements` | Create new engagement |
| `GET` | `/api/v1/engagements` | List engagements |
| `GET` | `/api/v1/engagements/{id}` | Get engagement with agent runs |
| `PATCH` | `/api/v1/engagements/{id}` | Update draft engagement |
| `POST` | `/api/v1/engagements/{id}/start` | Start agent orchestration |
| `POST` | `/api/v1/engagements/{id}/pause` | Pause & checkpoint agents |
| `POST` | `/api/v1/engagements/{id}/resume` | Resume from checkpoint |
| `GET` | `/api/v1/engagements/{id}/findings` | Get all findings |
| `GET` | `/api/v1/agents/{run_id}` | Get agent run status |
| `WS` | `/ws/agent-status` | Real-time agent events |

---

## ⚙️ Environment Variables

| Variable | Description |
|---|---|
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_ANON_KEY` | Supabase anonymous key |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase service role key |
| `DATABASE_URL` | PostgreSQL connection string (`postgresql+asyncpg://...`) |
| `REDIS_URL` | Redis connection string |
| `SECRET_KEY` | JWT signing key |
| `CREDENTIAL_ENCRYPTION_KEY` | 32-byte base64 key for AES-256-GCM |
| `OPENAI_API_KEY` | OpenAI API key (for LLM analysis) |
| `TINYFISH_API_KEY` | TinyFish browser automation key |

---

## 🧪 Testing

```bash
cd backend
source .venv/bin/activate
pytest tests/ -v
```

**20 tests** covering health checks, lead capture, engagement lifecycle, and agent orchestration — all passing in ~0.5s using in-memory SQLite.

---

## 🎨 Theming

KEEN supports **dark** and **light** themes, toggled via the sun/moon button in the navigation bar. Themes are implemented with CSS custom properties in `frontend/src/index.css` and managed through React context (`frontend/src/context/ThemeContext.tsx`).

---

## 🌐 Enterprise Integrations

KEEN connects to 15+ enterprise systems for live data extraction:

> Salesforce · NetSuite · SAP · Oracle · Dynamics · QuickBooks · HubSpot · Marketo · Bloomberg · CapIQ · PitchBook · SEC EDGAR · Sales Navigator · ZoomInfo · Crunchbase

---

## 📦 Build & Deployment

```bash
cd frontend
npm run build        # → frontend/dist/
```

Deploy the frontend to any static hosting (Vercel, Netlify, Cloudflare Pages). The backend runs as a standalone FastAPI service.

---

## 📋 License

© 2026 KEEN — Backed by TinyFish Accelerator
