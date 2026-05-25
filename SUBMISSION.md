# PharmAgent AI — OpenClaw Challenge Submission

## The problem

Community pharmacists in Scotland dispense thousands of prescriptions weekly with no AI-assisted safety net. Drug interaction checking is done manually, from memory or printed reference cards — a process that is slow, inconsistent, and error-prone for complex patients on five or more medications. Stock management is similarly manual: reorder decisions made on gut feel, expiry waste going untracked. Patient engagement (refill reminders) is often skipped entirely because there is no time.

These are not hypothetical problems. Adverse drug reactions from missed interactions account for an estimated 6.5% of hospital admissions in the UK. Most are preventable.

## The concept

PharmAgent AI is a multi-agent system that gives a pharmacist a clinical co-pilot — accessible from WhatsApp, Telegram, or a web dashboard — powered by Claude AI and integrated into their workflow via OpenClaw.

Seven specialist agents handle distinct domains, coordinated by an Orchestrator that accepts plain English and decides which agents to invoke.

## Agents

**Orchestrator Agent** — the single entry point for all natural language requests. Resolves patient names to CHI numbers automatically, coordinates sub-agents in sequence, and synthesises all outputs into a unified NHS-format clinical report.

**Interaction Safety Agent** — cross-references a patient's active prescriptions against a new medication before dispensing. Risk ratings are anchored to 80 validated drug pairs from DrugBank 6.0 and Micromedex: Claude cannot downgrade a HIGH interaction to MODERATE. When a known pair is detected, the full clinical management record — safer alternatives, monitoring steps, mechanism of action — is injected directly into the prompt. Returns structured data (severity, mechanism, safer alternative, evidence source per interaction) rather than raw text.

**Stock Intelligence Agent** — reviews inventory levels, flags near-expiry medications, calculates waste cost, and triggers supplier reorders automatically. Predicts future shortages by calculating days of supply from active prescription demand — flags medications that will run out within 30 days even if currently above the reorder threshold. Auto-reorders use a smart quantity (2-month demand buffer) rather than a fixed number.

**Patient Engagement Agent** — generates personalised SMS/email refill reminders for patients due within a configurable window. Patients are scored for adherence risk using population statistics derived from a 5,000-record dataset; high-risk patients (elderly, complex regimens, mental health medications) are prioritised and receive more supportive messaging. The `adherence_check` campaign type specifically targets overdue patients who have not collected — connecting anomaly detection to clinical action.

**Handover Agent** — generates a structured NHS shift handover note covering the last 12 hours of audit activity, stock alerts, patients due for urgent refill within 3 days, and any HIGH-risk interaction flags from the shift. Designed for end-of-shift use.

**Emergency Supply Agent** — processes emergency medication supply requests when a patient has run out and cannot reach their GP. Resolves the patient by CHI or name, runs an interaction check on the supplied medication, and generates a legally formatted NHS Scotland supply record including the 72-hour prescriber notification requirement and 2-year record retention reminder.

**Analytics Agent** — three predictive capabilities:
- *Patient prioritisation*: scores every patient by urgency (overdue days × 3 + adherence risk + number of medications) and returns a sorted URGENT / HIGH / ROUTINE list for the pharmacist.
- *Anomaly detection*: identifies overdue collections, polypharmacy patients (5+ active medications), emergency supply frequency spikes, and medications with fewer than 14 days of stock at current demand.
- *Workflow optimisation*: analyses audit history and prescription demand patterns to generate concrete improvement recommendations with IMMEDIATE / THIS WEEK / NEXT MONTH timeframes.

## Technical architecture

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
- Demand forecasting              - StockIntelligenceAgent
- Audit logging                   - PatientEngagementAgent
- Message dispatch                - HandoverAgent
- Anomaly signals                 - EmergencySupplyAgent
                                  - AnalyticsAgent
```

The tool/agent separation is intentional. Every database query, reorder, and message dispatch is handled by deterministic Python functions — auditable, testable, and replaceable without touching the AI layer. Claude only handles reasoning: interpreting intent, weighing clinical risk, generating human-readable output.

## Real clinical datasets

Two validated datasets are integrated directly into the agent layer:

**Drug-Drug Interaction database** (`data/Interaction Safety Agent.json`) — 80 records sourced from DrugBank 6.0, Micromedex Solutions, and FDA Drug Safety Communications. Loaded at startup into the Interaction Safety Agent. Each record includes severity (Major/Moderate/Minor), mechanism of action, clinical effect, safer alternative, and specific clinical management steps. When a patient's medication list matches a known pair, the full management record is injected into the Claude prompt, so recommendations cite evidence-based guidance rather than generic advice. DDI matching uses both brand name and generic name to avoid false negatives.

**Patient Adherence dataset** (`data/patient_adherence_dataset.csv`) — 5,000 records with 14 demographic and clinical features. Non-adherence rates by age band derived from this data: 52% for under-45s rising to 61% for 75+, with an 11 percentage point uplift for patients on mental health medications. These statistics are used by the Patient Engagement Agent to score every patient's adherence risk (HIGH / MEDIUM / LOW) before each campaign run. High-risk patients are sorted to the front of the outreach queue and receive warmer, more supportive messages tailored to their risk profile.

Both datasets are excluded from the repository (`.gitignore`) and loaded at runtime. The system falls back to hardcoded equivalents on Railway where the `data/` folder is absent, so the live demo is unaffected.

## Key safety decisions

1. **Deterministic interaction rules** — 80 clinically validated drug pairs with fixed severity levels injected into every interaction check. Claude reasons around them; it cannot override them.
2. **Human-in-the-loop** — every agent recommendation requires pharmacist sign-off before clinical action is taken. The system advises; it does not dispense.
3. **Full audit trail** — every agent action is logged to a timestamped `AuditLog` table with agent identity and patient reference, satisfying NHS Scotland regulatory requirements.
4. **CHI number validation (Modulus 11)** — Scottish CHI numbers are validated against the official NHS Scotland Modulus 11 check-digit algorithm before any patient query reaches the database. A single transposed digit on a 10-digit CHI would silently match the wrong patient, meaning the interaction check would run against the wrong person's medications. Modulus 11 catches this at the API boundary — the request is rejected before it reaches the database.
5. **Data residency** — designed for deployment within DataVita's Scottish data centres, keeping patient data within Scotland per NHS Scotland GDPR requirements.
6. **API key protection** — under UK GDPR, patient records require explicit access controls. All endpoints except `/health` and `/demo` require an `X-API-Key` header enforced server-side. Without this, the live deployment would expose all patient medication histories publicly. The dashboard sends the key automatically — judges do not need to enter anything.
7. **Rate limiting** — agent endpoints are rate-limited (30/minute general, 10/minute analytics) via `slowapi` to prevent API abuse and runaway AI costs in a shared deployment.
8. **Dataset governance** — the DrugBank interaction data and patient adherence dataset are excluded from the repository (`.gitignore`). DrugBank 6.0 has licensing restrictions that prohibit public redistribution; the adherence dataset is derived from real patient records and cannot be committed to a public repo. The system falls back to hardcoded equivalents on Railway so the live demo is unaffected.
9. **Demand-based stock forecasting** — days of supply is calculated as `current_stock ÷ active_prescriptions`, not threshold comparison. This flags medications as shortage-risk even when they are above the reorder threshold, if prescription demand is high enough to exhaust stock within 14 days.

## OpenClaw integration

Seven skills connect PharmAgent to any chat app via OpenClaw:

| Skill | Trigger |
|---|---|
| `pharmagent-daily-briefing` | "Run the daily pharmacy check" |
| `pharmagent-interaction-check` | "Check CHI 1203480016 for Ibuprofen" |
| `pharmagent-patient-profile` | "What is Margaret Campbell on?" |
| `pharmagent-handover` | "Generate handover notes" |
| `pharmagent-emergency-supply` | "Emergency supply for Robertson — he's run out of Warfarin" |
| `pharmagent-stock-review` | "What's running low?" |
| `pharmagent-engagement-campaign` | "Send refill reminders this week" |
| `pharmagent-analytics` | "Prioritise my patients", "Any anomalies today?", "How can I optimise the workflow?" |

The daily briefing skill can be scheduled as a cron task in OpenClaw, delivering an automated 08:00 weekday briefing to the pharmacist's phone.

> **Note for judges running locally:** The SKILL.md files point to the Railway deployment URL. If self-hosting, update the base URL in each skill file or set the `PHARMAGENT_API_URL` environment variable.

## Dashboard

The web dashboard demonstrates the full system in one place:

- **Daily Briefing** — single button triggers all agents via the Orchestrator and returns a unified NHS-style clinical report. Downloadable as PDF.
- **Drug Interaction Checker** — CHI + new medication → structured risk report with severity, mechanism, safer alternative, and evidence source per detected interaction. Quick-fill demo chips for instant testing.
- **Stock Review** — AI highlights (critical stock, predicted shortages, auto-orders placed, £ expiry waste) followed by the full reorder and expiry lists with inline reorder buttons.
- **Patient Lookup** — full medication profile by CHI number or patient name.
- **Patient Engagement** — personalised SMS/email campaigns across 9 types. Overdue patient outreach (adherence check) pulls directly from the anomaly detection pipeline.
- **Audit Log** — live table of all agent actions with timestamp, agent identity, and detail.
- **Analytics** — three views driven by the Analytics Agent: patient prioritisation (urgency-scored patient cards grouped URGENT / HIGH / ROUTINE), anomaly detection (overdue collections, polypharmacy flags, stock shortage risk rendered as structured cards, not raw text), and workflow optimisation (AI recommendations parsed by timeframe and displayed as IMMEDIATE / THIS WEEK / NEXT MONTH action rows).

## Live demo

| | |
|---|---|
| **Dashboard** | https://web-production-1f27a.up.railway.app/static/dashboard.html |
| **API docs** | https://web-production-1f27a.up.railway.app/docs |
| **Health** | https://web-production-1f27a.up.railway.app/health |

### Demo videos

| | |
|---|---|
| **Dashboard walkthrough** | https://youtu.be/lOdH7-khP-g |
| **WhatsApp integration** | https://youtu.be/BmkHsPRh1uE |

All 10 demo patients are seeded. Quick-fill buttons in the dashboard auto-populate the forms — no CHI number memorisation needed.

| CHI | Patient | Try checking against |
|---|---|---|
| `1203480016` | Margaret Campbell | Ibuprofen, Amiodarone |
| `2407550013` | James Morrison | Amiodarone, Warfarin |
| `0811620018` | Patricia Henderson | Ibuprofen, Ramipril |
| `3004710013` | Robert MacLeod | Ibuprofen, Paracetamol |
| `1509580018` | Susan Graham | Tramadol, Amitriptyline |
| `0312430019` | William Stevenson | Clarithromycin, Ibuprofen |
| `1902670019` | Dorothy Reid | Ibuprofen, Aspirin |
| `2706800011` | George Fraser | Warfarin, Ibuprofen |
| `1108530028` | Helen Murray | Propranolol, Ibuprofen |
| `2201380015` | Thomas Robertson | Aspirin, Amiodarone (already on Warfarin + Ibuprofen) |

## Repository

https://github.com/Maricikam/pharmagent
