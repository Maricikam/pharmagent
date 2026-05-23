# PharmAgent AI

**Intelligent pharmacy management powered by Claude AI and OpenClaw — built for the DataVita OpenClaw Challenge.**

PharmAgent AI is a multi-agent system that helps pharmacists check drug interactions, manage stock, and engage patients — all from a web dashboard or directly over WhatsApp via OpenClaw.

---

## Live Demo

| | |
|---|---|
| **Dashboard** | [web-production-1f27a.up.railway.app/static/dashboard.html](https://web-production-1f27a.up.railway.app/static/dashboard.html) |
| **API docs** | [web-production-1f27a.up.railway.app/docs](https://web-production-1f27a.up.railway.app/docs) |
| **Health check** | [web-production-1f27a.up.railway.app/health](https://web-production-1f27a.up.railway.app/health) |

### WhatsApp demo (via OpenClaw)

The system is connected to WhatsApp via OpenClaw. Example conversations:

> *"Check patient 4823719056 for Ibuprofen"*
> → **CONTRAINDICATED** — Warfarin + Ibuprofen: major bleeding risk. DO NOT prescribe. Alternative: paracetamol.

> *"What's running low on stock?"*
> → Critical: Ramipril 5mg (8 units), Aspirin 75mg (18 units), Amoxicillin 500mg (12 units) — with reorder recommendations.

> *"Send refill reminders to patients due this week"*
> → 13 prescriptions due — 6 patients contacted with personalised SMS messages.

---

## What it does

PharmAgent AI runs three specialist AI agents, coordinated by an Orchestrator:

| Agent | Responsibility |
|---|---|
| **Interaction Safety Agent** | Checks a patient's active prescriptions against a new medication. Anchors risk ratings to a deterministic clinical rules table — the AI cannot downgrade a HIGH risk rating. |
| **Stock Intelligence Agent** | Reviews inventory levels, flags near-expiry medications, calculates waste cost, and triggers supplier reorders. |
| **Patient Engagement Agent** | Identifies patients due for refills and generates personalised SMS/email reminders via Claude. |
| **Orchestrator Agent** | Accepts plain-English intents and coordinates the sub-agents in sequence. |

---

## Architecture

```
WhatsApp / Dashboard
        │
        ▼
  OpenClaw Gateway          ← routes natural language to skills
        │
        ▼
  FastAPI Backend (Railway)
        │
   ┌────┴────────────────────────┐
   │                             │
   ▼                             ▼
Tool Layer                  Agent Layer
(deterministic)             (Claude Haiku)
- DB queries                - InteractionSafetyAgent
- Stock checks              - StockIntelligenceAgent
- Audit logging             - PatientEngagementAgent
- Message sending           - OrchestratorAgent
```

All patient data is stored in the configured database. In production, this would be deployed within DataVita's Scottish data centres, satisfying NHS Scotland GDPR requirements.

---

## OpenClaw integration

Four OpenClaw skills are included in the `skills/` directory:

| Skill | Trigger |
|---|---|
| `pharmagent-interaction-check` | "Check patient [CHI] for [medication]" |
| `pharmagent-stock-review` | "What's running low on stock?" |
| `pharmagent-patient-engagement` | "Send refill reminders this week" |
| `pharmagent-morning-briefing` | "Good morning, run the pharmacy check" |

See [OPENCLAW.md](OPENCLAW.md) for full setup instructions.

---

## Local setup

### Prerequisites
- Python 3.11+
- An [Anthropic API key](https://console.anthropic.com)

### Steps

```bash
# 1. Clone
git clone https://github.com/Maricikam/pharmagent
cd pharmagent

# 2. Create virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY

# 5. Seed the database with demo data
python scripts/seed.py

# 6. Run the demo (all agents, no server needed)
python run_demo.py

# 7. Or start the API server
uvicorn api.main:app --reload
# Dashboard: http://localhost:8000/static/dashboard.html
# API docs:  http://localhost:8000/docs
```

### Demo CHI numbers (seeded test data)

| CHI | Patient | Notable medications |
|---|---|---|
| `4823719056` | Margaret Campbell | Warfarin, Aspirin, Atorvastatin |
| `7384920156` | Thomas Robertson | Metformin, Lisinopril |
| `2847563019` | Elizabeth Fraser | Sertraline, Omeprazole |

---

## API reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | System status, AI mode |
| `GET` | `/demo` | Full demo response (no API key needed) |
| `GET` | `/patients/{chi}` | Patient lookup by CHI number |
| `GET` | `/stock/low` | Medications below reorder threshold |
| `GET` | `/stock/expiring` | Medications expiring within 30 days |
| `POST` | `/stock/reorder` | Place a supplier reorder |
| `POST` | `/agents/interaction-check` | Run Interaction Safety Agent |
| `GET` | `/agents/interaction-check` | Same — GET version for OpenClaw |
| `POST` | `/agents/stock-review` | Run Stock Intelligence Agent |
| `GET` | `/agents/stock-review` | Same — GET version for OpenClaw |
| `POST` | `/agents/engagement-campaign` | Run Patient Engagement Agent |
| `GET` | `/agents/engagement-campaign` | Same — GET version for OpenClaw |
| `POST` | `/agents/orchestrate` | Plain-English orchestration |

All data endpoints require an `X-API-Key` header if `API_KEY` is set in the environment.

---

## Running tests

```bash
# Tool layer tests run without any API key
pytest tests/TestToolLayer -v

# Agent tests require a live API key
export ANTHROPIC_API_KEY=your-key-here   # Windows: set ANTHROPIC_API_KEY=...
pytest tests/ -v
```

---

## Project structure

```
pharmagent/
├── agents/
│   ├── interaction_safety_agent.py   # Drug interaction checking
│   ├── stock_intelligence_agent.py   # Inventory management
│   ├── patient_engagement_agent.py   # Refill reminders
│   └── orchestrator_agent.py         # Multi-agent coordination
├── tools/
│   └── pharmacy_tools.py             # Deterministic DB tools
├── db/
│   ├── models.py                     # SQLAlchemy models
│   ├── database.py                   # Connection management
│   └── session.py                    # Session factory
├── api/
│   ├── main.py                       # FastAPI application
│   └── static/dashboard.html         # Web dashboard
├── skills/                           # OpenClaw skill definitions
│   ├── pharmagent-interaction-check/
│   ├── pharmagent-stock-review/
│   ├── pharmagent-patient-engagement/
│   └── pharmagent-morning-briefing/
├── tests/
├── scripts/
│   └── seed.py                       # Demo data seeder
├── run_demo.py                        # CLI demo runner
├── openclaw.json                      # OpenClaw config template
└── requirements.txt
```

---

## Deployment

Deployed on [Railway](https://railway.app) free tier. Uses PostgreSQL on Railway in production, SQLite locally.

Environment variables required:
```
ANTHROPIC_API_KEY=   # Claude API key
DATABASE_URL=        # PostgreSQL URL (Railway provides this)
API_KEY=             # Access key for protected endpoints
```
