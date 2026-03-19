# KEEN

**AI that does your due diligence homework for you.**

> 🌐 **Try it live:** [keen-sigma.vercel.app](https://keen-sigma.vercel.app) — no account needed
>
> Built at [TinyFish Accelerator](https://www.tinyfish.ai/accelerator) (2026 cohort)

---

## So what even is this?

Imagine a private equity firm is thinking about buying a company. Before they write a big check, they need to dig into that company's finances, customers, contracts, software — basically everything. This process is called **due diligence** and it usually takes a team of analysts weeks to do manually.

KEEN does that job automatically.

You tell it the company name, click a button, and it goes off and reads financial systems, CRM databases, public filings, LinkedIn, and more — then comes back with a clear list of red flags, discrepancies, and things that need a second look. Like having a really fast analyst who never sleeps and doesn't charge by the hour.

---

## Try it in 5 minutes (no sign-up needed)

**Go to:** [keen-sigma.vercel.app](https://keen-sigma.vercel.app)

### 1. Check everything's working
Click **STATUS** in the top bar. If you see a green **OPERATIONAL** badge, you're good to go.

### 2. Make sure Demo mode is on
Look for the little amber **DEMO** pill in the top right. If it says **LIVE**, click it once to switch to demo. Demo mode uses fake (but realistic) data so you don't need to connect anything real.

### 3. Open the Dashboard
Click **DASHBOARD**. No login needed in demo mode. It'll automatically create a test company called "Zendesk Inc" and start running the analysis.

### 4. Watch it work
Three AI agents run one after another — Research, Analysis, then Delivery. You can see exactly what each one is doing in real time. The whole thing takes a couple of minutes.

### 5. Look at the findings
Once it's done, click the **RESULTS** tab. You'll see a list of things KEEN found — like:

- Revenue numbers that don't match between two systems (a $1.3M gap)
- A sales funnel that's leaking more leads than it should
- An engineer who left the company that nobody flagged
- Overdue customer invoices that are 4+ months old

### 6. Export the report
Hit **PDF** or **XLSX** to download a proper report you could actually hand to someone.

---

## What it actually does under the hood

*(Feel free to skip this bit — but here's a plain-English explanation if you're curious)*

### Step 1: Research
KEEN connects to a bunch of business software systems — things like Salesforce (where sales teams track deals), NetSuite (accounting software), SEC EDGAR (US government company filings), HubSpot (marketing data), and Crunchbase (startup funding info).

For systems that don't have a simple connection, it uses a tool called **TinyFish** that literally opens a web browser, logs in, and reads the data like a human would — except automatically. Think Bloomberg, LinkedIn, SAP, Oracle, and others.

It pulls all of this data together into one place.

### Step 2: Analysis
An AI (Claude, made by Anthropic) then reads through all that data and looks for things that don't add up. If the sales system says revenue is $10M but the accounting system says $8.7M — that's a red flag. It flags these discrepancies, scores how serious they are, and marks the ones that need a human to double-check.

### Step 3: Delivery
Finally, it writes up a proper report — executive summary, full findings, everything — and can automatically send it to Slack, email, Google Drive, or SharePoint.

---

## What's built and working

| Feature | Status |
|---|---|
| Full 3-step AI pipeline (Research → Analysis → Delivery) | ✅ Works |
| Demo mode with realistic fake data | ✅ Works |
| 5 live data connections (Salesforce, NetSuite, SEC, HubSpot, Crunchbase) | ✅ Works |
| Browser automation for locked-down systems (via TinyFish) | ✅ Works |
| PDF and Excel report export | ✅ Works |
| Auto-send to Slack, email, Google Drive, SharePoint | ✅ Works |
| Upload your own documents (PDF, Excel, Word, etc.) | ✅ Works |
| Expert call transcripts (integrates with Tegus, Third Bridge) | ✅ Works |
| Deal comparison against similar deals (benchmarking) | ✅ Works |
| Ongoing monitoring of a company after acquisition | ✅ Works |
| Legal contract scanning | ✅ Works |
| Technical review of a company's GitHub codebase | ✅ Works |
| Unique URL for each analysis (shareable, refresh-safe) | ✅ Works |
| Sign in / accounts (so your work is saved) | ✅ Works |
| Billing / pricing | 🔲 Not built yet |
| Admin tools | 🔲 Not built yet |

---

## Demo mode vs. Live mode

| | Demo | Live |
|---|---|---|
| What you see | Fake "Zendesk Inc" data | Real data from your actual connected systems |
| Credentials needed | None | You'll need to connect your accounts |
| Good for | Showing people how it works | Actually using it for a real deal |
| How to toggle | Amber **DEMO** pill in the top right | Green **LIVE** pill |

---

## Want to run it yourself locally?

You'll need a few things installed on your computer first:
- Node.js (for the website part)
- Python 3.11+ (for the AI engine)
- Redis (a fast database, used for caching)
- A free Supabase account (handles login)

### Website (frontend)
```bash
cd frontend
npm install
cp .env.example .env.local    # add your Supabase details
npm run dev                    # opens at http://localhost:5173
```

### AI engine (backend)
```bash
cd backend

python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

cp .env.example .env
# Fill in the details (database, Supabase, at least one AI key)

alembic upgrade head           # sets up the database tables
uvicorn app.main:app --reload --port 8000
```

### Generate a secret key (you'll need this once)
```bash
python3 -c "import base64, os; print(base64.b64encode(os.urandom(32)).decode())"
```

---

## Environment variables (the settings it needs)

### Backend — required
| Variable | What it's for |
|---|---|
| `DATABASE_URL` | Where the database lives |
| `REDIS_URL` | Where the fast cache lives |
| `SECRET_KEY` | A random secret the app uses internally |
| `CREDENTIAL_ENCRYPTION_KEY` | Encrypts any API keys you enter |
| `SUPABASE_URL` | Your Supabase project address |
| `SUPABASE_ANON_KEY` | Supabase public key |
| `CORS_ORIGINS` | Which websites are allowed to talk to the backend |

### AI keys — need at least one
| Variable | Which AI |
|---|---|
| `ANTHROPIC_API_KEY` | Claude (this is the main one) |
| `GEMINI_API_KEY` | Google Gemini (backup) |
| `GROQ_API_KEY` | Groq (backup backup) |

### For live mode
| Variable | What it unlocks |
|---|---|
| `TINYFISH_API_KEY` | Browser automation for Bloomberg, LinkedIn, SAP, Oracle, and more |

### Frontend — required
| Variable | What it's for |
|---|---|
| `VITE_API_URL` | Where the backend is (e.g. `https://keen-backend.fly.dev`) |
| `VITE_SUPABASE_URL` | Supabase project address |
| `VITE_SUPABASE_ANON_KEY` | Supabase public key |

---

## How it's deployed (the live version)

- **Website** → hosted on Vercel (auto-deploys whenever code is pushed to GitHub)
- **AI engine** → hosted on Fly.io
- **Database** → Supabase (managed, so we don't have to worry about it)
- **Cache** → Redis on Fly.io

---

## License

© 2026 KEEN — Backed by [TinyFish Accelerator](https://www.tinyfish.ai/accelerator)
