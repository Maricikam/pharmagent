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
└──────────┬──────────────┬──────────────────┬────────────────┘
           │              │                  │
┌──────────▼──┐  ┌────────▼───────┐  ┌──────▼──────────────┐
│ Interaction │  │    Stock       │  │     Patient         │
│   Safety   │  │ Intelligence   │  │   Engagement        │
│   Agent    │  │    Agent       │  │     Agent           │
└──────────┬──┘  └────────┬───────┘  └──────┬──────────────┘
           │              │                  │
┌──────────▼──────────────▼──────────────────▼──────────────┐
│                      TOOL LAYER                            │
│   DB queries · Stock checks · Supplier API · Audit log    │
│   Patient lookup · Message dispatch · Prescription fetch  │
└─────────────────────────┬─────────────────────────────────┘
                          │
┌─────────────────────────▼─────────────────────────────────┐
│                    DATA LAYER                              │
│         PostgreSQL (DataVita Scottish infrastructure)      │
│    Patients · Prescriptions · Inventory · Audit Logs      │
└───────────────────────────────────────────────────────────┘
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

Three specialist agents, each with a bounded domain of responsibility. Each agent receives tool outputs and applies Claude reasoning to generate decisions, recommendations, or actions.

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

Four AgentSkills-compatible `SKILL.md` files teach an OpenClaw instance how to call PharmAgent from any connected chat app (WhatsApp, Telegram, Discord).

| Skill | Triggers | Calls |
|---|---|---|
| `pharmagent-daily-briefing` | "Good morning, run the check" | `POST /agents/orchestrate` |
| `pharmagent-interaction-check` | "Check patient before I dispense" | `POST /agents/interaction-check` |
| `pharmagent-stock-review` | "What's running low?" | `POST /agents/stock-review` |
| `pharmagent-patient-engagement` | "Send SMS reminders" | `POST /agents/engagement-campaign` |

The daily briefing skill can also be scheduled as a cron task in OpenClaw, delivering an automated 08:00 weekday briefing to the pharmacist's phone.

---

## API Layer

**Location:** `api/main.py`

FastAPI application exposing all agent functionality as HTTP endpoints. Includes:

- `GET /health` — system status and AI readiness check
- `GET /demo` — full showcase of all three agents (no auth required)
- `GET /docs` — interactive Swagger UI for judges and developers
- `POST /agents/orchestrate` — plain English intent routing
- `POST /agents/interaction-check` — interaction safety check
- `POST /agents/stock-review` — stock intelligence review
- `POST /agents/engagement-campaign` — patient engagement campaign
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
- **Data residency:** Designed for DataVita Scottish data centres — patient data stays within Scotland (NHS Scotland GDPR / NFR-01)
- **Encryption:** AES-256 at rest, TLS 1.3 in transit (production configuration)
- **No secrets in code:** API keys via environment variables only; `.env` excluded from git

---