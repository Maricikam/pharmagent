# PharmAgent AI

**Intelligent pharmacy management powered by Claude AI and OpenClaw — built for the DataVita OpenClaw Challenge.**

PharmAgent AI is a multi-agent system that helps pharmacists check drug interactions, manage stock, engage patients, and detect clinical anomalies — all from a web dashboard or directly over WhatsApp via OpenClaw.

### Dashboard features

| Feature | Description |
|---|---|
| **Daily Briefing** | One-click orchestrated workflow — runs all agents and returns a unified NHS clinical report. Downloadable as PDF. |
| **Drug Interaction Checker** | Check any patient's active medications against a new prescription. Returns structured results: severity, mechanism, safer alternative, evidence source. Quick-fill demo chips included. |
| **Stock Review** | AI highlights (critical items, predicted shortages, auto-orders placed, expiry waste value) with inline reorder buttons. |
| **Patient Lookup** | Full medication profile by CHI number or patient name. |
| **Patient Engagement** | Personalised SMS/email campaigns — 9 types including refill reminders, adherence check (overdue patients), flu vaccination, seasonal campaigns. |
| **Audit Log** | Live view of all agent actions logged for regulatory compliance. |
| **Analytics** | Patient prioritisation by clinical urgency (URGENT / HIGH / ROUTINE cards), anomaly detection across stock and patient behaviour, and workflow optimisation recommendations tagged by timeframe (IMMEDIATE / THIS WEEK / NEXT MONTH). |

---

## Live Demo

| | |
|---|---|
| **Dashboard** | [web-production-1f27a.up.railway.app/static/dashboard.html](https://web-production-1f27a.up.railway.app/static/dashboard.html) |
| **API docs** | [web-production-1f27a.up.railway.app/docs](https://web-production-1f27a.up.railway.app/docs) |
| **Health check** | [web-production-1f27a.up.railway.app/health](https://web-production-1f27a.up.railway.app/health) |

### Demo videos

| | |
|---|---|
| **Dashboard walkthrough** | [▶ Watch on YouTube](https://youtu.be/lOdH7-khP-g) |
| **WhatsApp integration** | [▶ Watch on YouTube](https://youtu.be/BmkHsPRh1uE) |

### WhatsApp demo (via OpenClaw)

> *"Check patient 1203480016 for Ibuprofen"*
> → **HIGH** — Warfarin + Ibuprofen: major bleeding risk. DO NOT dispense. Safer alternative: paracetamol.

> *"What's running low on stock?"*
> → Critical: Ramipril 5mg (8 units, 8 days supply). 3 medications predicted to run short within 30 days.

> *"Send refill reminders to patients due this week"*
> → 6 patients contacted — HIGH-risk patients prioritised, sent warmer supportive messages.

> *"Who needs attention today?"*
> → Patient prioritisation: URGENT (overdue collections) → HIGH (adherence risk) → ROUTINE.

---

## Agents

| Agent | Responsibility |
|---|---|
| **Orchestrator Agent** | Accepts plain-English intents, resolves patient names to CHI numbers, coordinates sub-agents in sequence, synthesises a unified NHS-format report. |
| **Interaction Safety Agent** | Checks a patient's active prescriptions against a new medication. Risk ratings anchored to 80 validated DDI pairs from DrugBank 6.0 / Micromedex — Claude cannot downgrade a HIGH rating. Full clinical management guidance injected into the prompt when a known pair is detected. Returns structured results: each interaction with severity, mechanism, safer alternative, evidence source. |
| **Stock Intelligence Agent** | Reviews inventory, flags near-expiry stock, predicts shortages based on prescription demand (days of supply calculation), and triggers smart reorders using a 2-month demand buffer rather than a fixed quantity. |
| **Patient Engagement Agent** | Identifies patients due for refills and generates personalised SMS/email messages. Patients scored for adherence risk using population statistics from a 5,000-record dataset — HIGH-risk patients prioritised and receive more supportive messaging. `adherence_check` campaign type specifically targets overdue patients. |
| **Handover Agent** | Generates a structured NHS shift handover note — audit activity, stock alerts, patients due in 3 days, HIGH-risk interaction flags from the shift. |
| **Emergency Supply Agent** | Processes emergency medication supply requests. Resolves patient, runs interaction check, generates a legally formatted NHS Scotland supply record with 72-hour prescriber notification requirement and 2-year retention reminder. |
| **Analytics Agent** | Three capabilities: (1) patient prioritisation — urgency scores across the full patient list; (2) anomaly detection — overdue collections, polypharmacy flags, emergency supply spikes, 14-day stockout risks; (3) workflow optimisation — AI recommendations based on audit history and demand patterns. |

---

## Datasets

Two validated clinical datasets are integrated into the agent layer at runtime. Both are excluded from the repository (`.gitignore`) and loaded when present; the system falls back to hardcoded equivalents on Railway.

| Dataset | Records | Used by | Effect |
|---|---|---|---|
| `data/Interaction Safety Agent.json` | 80 DDI records | InteractionSafetyAgent | Each record includes severity, mechanism, safer alternative, and clinical management steps from DrugBank 6.0, Micromedex, and FDA communications. Matching records are injected into the Claude prompt at runtime. |
| `data/patient_adherence_dataset.csv` | 5,000 records | PatientEngagementAgent | Non-adherence rates by age band and comorbidity count derived at startup (75+: 61%, under-45: 52%, +11pp for mental health medications). Used to score every patient HIGH / MEDIUM / LOW before each campaign. |

To use locally, place the files in `data/` before running.

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
   ┌────┴──────────────────────────────┐
   │                                   │
   ▼                                   ▼
Tool Layer (deterministic)        Agent Layer (Claude)
- DB queries                      - OrchestratorAgent
- Stock checks                    - InteractionSafetyAgent
- Audit logging                   - StockIntelligenceAgent
- Message sending                 - PatientEngagementAgent
- Demand forecasting              - HandoverAgent
- Anomaly signals                 - EmergencySupplyAgent
                                  - AnalyticsAgent
```

All patient data is stored in the configured database. In production, this would be deployed within DataVita's Scottish data centres, satisfying NHS Scotland GDPR requirements.

---

## OpenClaw integration

Seven OpenClaw skills are included in the `skills/` directory:

| Skill | Trigger |
|---|---|
| `pharmagent-daily-briefing` | "Run the daily pharmacy check" |
| `pharmagent-interaction-check` | "Check patient [CHI] for [medication]" |
| `pharmagent-patient-profile` | "What is Margaret Campbell on?" |
| `pharmagent-handover` | "Generate handover notes" |
| `pharmagent-emergency-supply` | "Emergency supply for Robertson — he's run out of Warfarin" |
| `pharmagent-stock-review` | "What's running low on stock?" |
| `pharmagent-engagement-campaign` | "Send refill reminders this week" |
| `pharmagent-analytics` | "Prioritise my patients", "Any anomalies today?", "Optimise the workflow" |

See [OPENCLAW.md](OPENCLAW.md) for full setup instructions.

---

## Security

API endpoints support optional key-based access control via `X-API-Key` header or `?api_key=` query parameter. Set `API_KEY` as an environment variable on Railway to enable enforcement; leave it unset for open access (demo mode).

CHI numbers are validated against the Modulus 11 algorithm before any patient query reaches the database.

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
| `1203480016` | Margaret Campbell | Warfarin, Aspirin → try Ibuprofen |
| `2407550013` | James Morrison | Atorvastatin, Clarithromycin → try Amiodarone |
| `0811620018` | Patricia Henderson | Lisinopril, Spironolactone → try Ibuprofen |
| `3004710013` | Robert MacLeod | Metformin → try Ibuprofen |
| `1509580018` | Susan Graham | Sertraline → try Tramadol |
| `0312430019` | William Stevenson | Digoxin, Furosemide, Bisoprolol, Amiodarone → try Clarithromycin |
| `1902670019` | Dorothy Reid | Prednisolone, Alendronic Acid → try Ibuprofen |
| `2706800011` | George Fraser | Omeprazole, Clopidogrel → try Warfarin |
| `1108530028` | Helen Murray | Salbutamol, Beclometasone → try Propranolol |
| `2201380015` | Thomas Robertson | Warfarin + Ibuprofen (already prescribed together — critical) |

---

## API reference

### System
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | System status, AI mode |
| `GET` | `/demo` | Full demo response (no key needed) |

### Patients & Stock
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/patients/{chi}` | Patient lookup by CHI number |
| `GET` | `/stock/low` | Medications below reorder threshold |
| `GET` | `/stock/expiring` | Medications expiring within 30 days |
| `POST` | `/stock/reorder` | Place a supplier reorder |

### Agents
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/agents/interaction-check` | Run Interaction Safety Agent |
| `GET` | `/agents/interaction-check` | Same — GET version for OpenClaw |
| `POST` | `/agents/stock-review` | Run Stock Intelligence Agent (with shortage prediction) |
| `GET` | `/agents/stock-review` | Same — GET version |
| `POST` | `/agents/engagement-campaign` | Run Patient Engagement Agent |
| `GET` | `/agents/engagement-campaign` | Same — GET version |
| `GET` | `/agents/patient-profile` | Full medication profile by CHI or name |
| `GET` | `/agents/handover` | Generate shift handover note |
| `POST` | `/agents/emergency-supply` | Process emergency supply with legal record |
| `GET` | `/agents/emergency-supply` | Same — GET version for OpenClaw |
| `POST` | `/agents/orchestrate` | Plain-English orchestration |

### Analytics
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/agents/analytics/workload` | Prescriptions due per day for next 7 days |
| `GET` | `/agents/analytics/prioritize-patients` | Urgency-scored patient list |
| `GET` | `/agents/analytics/anomalies` | Anomaly detection report |
| `GET` | `/agents/analytics/workflow` | Workflow optimisation recommendations |

### Audit
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/audit/logs` | Recent audit trail entries |

All endpoints except `/health` and `/demo` require `X-API-Key` header if `API_KEY` is set in the environment.

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
│   ├── orchestrator_agent.py         # Multi-agent coordination
│   ├── interaction_safety_agent.py   # Drug interaction checking
│   ├── stock_intelligence_agent.py   # Inventory management + shortage prediction
│   ├── patient_engagement_agent.py   # Refill reminders + adherence risk scoring
│   ├── handover_agent.py             # Shift handover generation
│   ├── emergency_supply_agent.py     # NHS emergency supply records
│   └── analytics_agent.py           # Prioritisation, anomalies, workflow optimisation
├── tools/
│   └── pharmacy_tools.py             # Deterministic DB tools
├── db/
│   ├── models.py                     # SQLAlchemy models
│   ├── database.py                   # Connection management
│   └── session.py                    # Session factory
├── api/
│   ├── main.py                       # FastAPI application
│   └── static/dashboard.html         # Web dashboard
├── skills/
│   ├── pharmagent-daily-briefing/
│   ├── pharmagent-interaction-check/
│   ├── pharmagent-patient-profile/
│   ├── pharmagent-handover/
│   ├── pharmagent-emergency-supply/
│   ├── pharmagent-stock-review/
│   ├── pharmagent-engagement-campaign/
│   └── pharmagent-analytics/
├── data/                             # Clinical datasets (gitignored)
│   ├── Interaction Safety Agent.json # 80 DDI records (DrugBank 6.0 / Micromedex)
│   └── patient_adherence_dataset.csv # 5,000-record adherence study
├── tests/
├── scripts/
│   └── seed.py                       # Demo data seeder
├── run_demo.py                        # CLI demo runner
├── openclaw.json                      # OpenClaw config
└── requirements.txt
```

---

## Deployment

Deployed on [Railway](https://railway.app). Uses PostgreSQL on Railway in production, SQLite locally.

Environment variables required:
```
ANTHROPIC_API_KEY=   # Claude API key
DATABASE_URL=        # PostgreSQL URL (Railway provides this automatically)
API_KEY=             # Access key for protected endpoints
```
