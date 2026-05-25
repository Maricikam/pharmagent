# PharmAgent AI — Architecture

## Overview

PharmAgent follows a three-layer agent architecture as recommended by Anthropic's agent design documentation. The core principle: **classical software handles deterministic operations; AI agents handle ambiguous, multi-step reasoning tasks where rigid rule systems would fail.**

```
┌─────────────────────────────────────────────────────────────┐
│                     OPENCLAW LAYER                          │
│  WhatsApp / Telegram / Discord → OpenClaw Skills → API      │
└─────────────────────────┬───────────────────────────────────┘
                          │ HTTP
┌─────────────────────────▼───────────────────────────────────┐
│                  ORCHESTRATION LAYER                        │
│                   OrchestratorAgent                         │
│         Accepts plain English, routes to sub-agents         │
└───┬──────────┬──────────┬──────────┬──────────┬────────────┘
    │          │          │          │          │
┌───▼───┐ ┌───▼───┐ ┌────▼───┐ ┌───▼────┐ ┌───▼──────────┐
│Inter- │ │Stock  │ │Patient │ │Hand-   │ │Emergency     │
│action │ │Intel- │ │Engage- │ │over    │ │Supply        │
│Safety │ │ligence│ │ment    │ │Agent   │ │Agent         │
└───┬───┘ └───┬───┘ └────┬───┘ └───┬────┘ └───┬──────────┘
    │         │          │         │           │
┌───▼─────────▼──────────▼─────────▼───────────▼──────────┐
│                      TOOL LAYER                          │
│  DB queries · Stock checks · Supplier API · Audit log   │
│  Patient lookup · Message dispatch · Anomaly signals    │
└─────────────────────────┬────────────────────────────────┘
                          │
┌─────────────────────────▼────────────────────────────────┐
│                    DATA LAYER                            │
│        PostgreSQL (DataVita Scottish infrastructure)     │
│   Patients · Prescriptions · Inventory · Audit Logs     │
└──────────────────────────────────────────────────────────┘

                  AnalyticsAgent (read-only, no orchestration)
                  Calls tool layer directly for prioritisation,
                  anomaly detection, and workflow optimisation.
```

---

## Layer 1 — Tool Layer (Deterministic)

**Location:** `tools/pharmacy_tools.py`

The tool layer contains all deterministic, testable functions that interact with external systems. No AI is involved at this layer — every function has a predictable input and output.

| Tool function | Purpose |
|---|---|
| `get_patient_by_nhs()` | Retrieve patient record by NHS number |
| `get_active_prescriptions()` | Fetch a patient's current medications |
| `get_low_stock_items()` | Return medications below reorder threshold |
| `get_near_expiry_items()` | Return medications expiring within a window |
| `place_supplier_order()` | Trigger a reorder with a supplier API |
| `send_patient_message()` | Dispatch SMS or email via Twilio/NHS Notify |
| `log_audit_entry()` | Write a timestamped action to the audit trail |

**Why this matters:** By isolating all external calls in the tool layer, agent logic can be tested independently using mock tools. The tool layer can also be swapped (e.g. changing database or SMS provider) without touching agent code.

---

## Layer 2 — Agent Layer (AI Reasoning)

**Location:** `agents/`

Seven specialist agents, each with a bounded domain of responsibility. Each agent receives tool outputs and applies Claude reasoning to generate decisions, recommendations, or actions.

### Interaction Safety Agent
**File:** `agents/interaction_safety_agent.py`

Receives a patient's NHS number and a new medication name. Fetches their active prescription list via the tool layer, then uses Claude to cross-reference for contraindications, assess severity, and produce a structured clinical recommendation.

At startup the agent loads 80 validated drug-drug interaction records from `data/Interaction Safety Agent.json` (DrugBank 6.0, Micromedex, FDA Drug Safety Communications). These replace the hardcoded severity table and provide richer context: for each detected pair Claude receives the full mechanism, clinical effect, safer alternative, and management steps — not just a severity label. Falls back to hardcoded rules when the file is absent (Railway deployment).

**Output:** Risk report with severity (LOW / MODERATE / HIGH), mechanism of interaction, evidence-based management steps, and dispensing recommendation. Always requires pharmacist sign-off.

### Stock Intelligence Agent
**File:** `agents/stock_intelligence_agent.py`

Reviews current inventory state via the tool layer. Uses Claude to prioritise reorder actions, assess financial impact of near-expiry stock, and generate a human-readable stock health summary. Auto-triggers supplier orders for high-priority items.

**Output:** Stock summary with low-stock list, expiry alerts, estimated waste value, and auto-order references.

### Patient Engagement Agent
**File:** `agents/patient_engagement_agent.py`

Identifies patients with upcoming prescription due dates. Before generating messages, scores each patient's adherence risk using population statistics derived from `data/patient_adherence_dataset.csv` (5,000 records). Non-adherence rates by age band and comorbidity count are calculated at startup; a mental health medication proxy adds an 11 percentage point uplift where applicable. Patients are sorted highest-risk first, and the risk level (HIGH / MEDIUM / LOW) is passed into the Claude prompt so message tone adapts accordingly.

Uses Claude to generate a personalised message for each patient — tailored to their specific medication, name, history, and adherence risk — rather than sending a generic template.

**Output:** Campaign summary with per-patient message previews, delivery status, adherence risk scores, and risk factors per patient.

### Handover Agent
**File:** `agents/handover_agent.py`

Generates a structured NHS shift handover note covering the last 12 hours of audit activity, stock alerts, patients due for urgent refill within 3 days, and any HIGH-risk interaction flags raised during the shift.

**Output:** Structured handover report ready to hand to the incoming pharmacist.

### Emergency Supply Agent
**File:** `agents/emergency_supply_agent.py`

Processes emergency medication supply requests when a patient has run out and cannot reach their GP. Resolves the patient by CHI or name, runs a full interaction check on the supplied medication, and generates a legally formatted NHS Scotland supply record including the 72-hour prescriber notification requirement and 2-year record retention reminder.

**Output:** NHS-format emergency supply record with interaction check result and compliance checklist.

### Analytics Agent
**File:** `agents/analytics_agent.py`

Read-only agent — does not write to the database. Called directly (not via the Orchestrator) and exposes three predictive capabilities:

- **Patient prioritisation** — scores every active patient by clinical urgency (overdue days × 3 + adherence risk score × 20 + medication count). Returns a sorted URGENT / HIGH / ROUTINE list with medication names included for each patient, renderable as structured cards in the dashboard.
- **Anomaly detection** — identifies overdue collections, polypharmacy patients (5+ active medications), emergency supply frequency spikes, and medications with fewer than 14 days of stock at current prescription demand.
- **Workflow optimisation** — analyses recent audit history and prescription demand patterns to generate concrete recommendations tagged `[IMMEDIATE]`, `[THIS WEEK]`, or `[NEXT MONTH]`.

Exposed via the dashboard **Analytics tab** (three sub-buttons: Patient prioritisation, Anomaly detection, Workflow optimisation) and via the `pharmagent-analytics` OpenClaw skill.

**Output:** Structured patient cards with urgency scores and medication lists; anomaly signal counts with per-patient detail; timeframe-tagged workflow recommendations.

---

## Layer 3 — Orchestration Layer

**Location:** `agents/orchestrator_agent.py`

The Orchestrator accepts plain English from a pharmacist and coordinates the specialist agents. It uses Claude to interpret intent, decompose tasks, delegate to the right agents, and synthesise a unified response.

**Example:**
```
Input:  "Good morning. Check stock and send reminders to patients due this week."
Action: → StockIntelligenceAgent (stock review + reorders)
        → PatientEngagementAgent (7-day window, SMS channel)
Output: Unified daily briefing combining both agent reports
```

The Orchestrator is the single entry point for all natural language requests, whether they come from the FastAPI endpoint or via OpenClaw skills.

---

## OpenClaw Integration

**Location:** `skills/`

Eight AgentSkills-compatible `SKILL.md` files teach an OpenClaw instance how to call PharmAgent from any connected chat app (WhatsApp, Telegram, Discord).

| Skill | Triggers | Calls |
|---|---|---|
| `pharmagent-daily-briefing` | "Good morning, run the check" | `POST /agents/orchestrate` |
| `pharmagent-interaction-check` | "Check patient before I dispense" | `POST /agents/interaction-check` |
| `pharmagent-stock-review` | "What's running low?" | `POST /agents/stock-review` |
| `pharmagent-patient-engagement` | "Send SMS reminders" | `POST /agents/engagement-campaign` |
| `pharmagent-patient-profile` | "What is Margaret on?" | `GET /agents/patient-profile` |
| `pharmagent-handover` | "Generate handover notes" | `GET /agents/handover` |
| `pharmagent-emergency-supply` | "Emergency supply for Robertson" | `POST /agents/emergency-supply` |
| `pharmagent-analytics` | "Prioritise my patients", "Any anomalies?" | `GET /agents/analytics/*` |

The daily briefing skill can also be scheduled as a cron task in OpenClaw, delivering an automated 08:00 weekday briefing to the pharmacist's phone.

---

## API Layer

**Location:** `api/main.py`

FastAPI application exposing all agent functionality as HTTP endpoints. Includes:

- `GET /health` — system status and AI readiness check
- `GET /demo` — full showcase response (no auth required)
- `GET /docs` — interactive Swagger UI
- `POST /agents/orchestrate` — plain English intent routing
- `POST /agents/interaction-check` — interaction safety check
- `POST /agents/stock-review` — stock intelligence review
- `POST /agents/engagement-campaign` — patient engagement campaign
- `GET /agents/patient-profile` — full medication profile by CHI or name
- `GET /agents/handover` — shift handover note
- `POST /agents/emergency-supply` — emergency supply record with interaction check
- `GET /agents/analytics/prioritize-patients` — urgency-scored patient list
- `GET /agents/analytics/anomalies` — anomaly detection report
- `GET /agents/analytics/workflow` — workflow optimisation recommendations
- `GET /agents/analytics/workload` — prescriptions due per day (no AI call)
- `GET /audit/logs` — recent audit trail entries (NFR-04 compliance)

**Live:** https://web-production-1f27a.up.railway.app

---

## Datasets

Two validated clinical datasets are loaded at agent startup and excluded from the repository (`.gitignore`). The system falls back to hardcoded equivalents on Railway where the `data/` folder is absent.

| File | Records | Source | Used by |
|---|---|---|---|
| `data/Interaction Safety Agent.json` | 80 | DrugBank 6.0, Micromedex, FDA Drug Safety Communications | InteractionSafetyAgent |
| `data/patient_adherence_dataset.csv` | 5,000 | Patient adherence study (14 demographic and clinical features) | PatientEngagementAgent |

**Why this matters architecturally:** The datasets sit outside the tool layer (which is purely deterministic DB access) and outside the data layer (which is transactional patient data). They form a separate read-only knowledge layer loaded once at agent startup — consistent with the principle that Claude operates on well-structured context rather than raw data. The tool layer remains unchanged; all dataset logic lives in the agents themselves.

---

## Design Patterns

| Pattern | Where used | Why |
|---|---|---|
| Orchestrator | `OrchestratorAgent` | Single entry point; separation of concerns |
| Tool Abstraction | `pharmacy_tools.py` | Swap data sources without changing agent logic |
| Observer | `StockIntelligenceAgent` | Reacts to inventory state rather than polling |
| Repository | `db/` layer | Separates persistence from agent business logic |

---

## Security and Compliance

- **Human-in-the-loop:** All agent recommendations require pharmacist approval before clinical action
- **Audit trail:** Every agent action logged with timestamp, agent identity, and action detail — visible in the dashboard Audit Log tab (`GET /audit/logs`)
- **CHI validation (Modulus 11):** Every CHI number is validated against the official NHS Scotland Modulus 11 check-digit algorithm before any DB query. A transposed digit would silently match the wrong patient; validation rejects malformed CHI numbers at the API boundary.
- **API key protection:** All patient-facing endpoints require `X-API-Key` header (enforced via FastAPI `Security` dependency). Satisfies UK GDPR access control requirements for patient data.
- **Rate limiting:** Agent endpoints rate-limited via `slowapi` (30/minute general; 10/minute analytics) to prevent abuse and runaway AI costs.
- **Dataset governance:** Clinical datasets excluded from the repository (`.gitignore`). DrugBank licensing prohibits public redistribution; the adherence dataset is derived from real patient records. System falls back to hardcoded equivalents when files are absent.
- **Data residency:** Designed for DataVita Scottish data centres — patient data stays within Scotland (NHS Scotland GDPR / NFR-01)
- **Encryption:** AES-256 at rest, TLS 1.3 in transit (production configuration)
- **No secrets in code:** API keys via environment variables only; `.env` excluded from git

---