# PharmAgent AI — OpenClaw Challenge Submission

## The problem

Community pharmacists in Scotland dispense thousands of prescriptions weekly with no AI-assisted safety net. Drug interaction checking is done manually, from memory or printed reference cards — a process that is slow, inconsistent, and error-prone for complex patients on five or more medications. Stock management is similarly manual: reorder decisions made on gut feel, expiry waste going untracked. Patient engagement (refill reminders) is often skipped entirely because there is no time.

These are not hypothetical problems. Adverse drug reactions from missed interactions account for an estimated 6.5% of hospital admissions in the UK. Most are preventable.

## The concept

PharmAgent AI is a multi-agent system that gives a pharmacist a clinical co-pilot — accessible from WhatsApp, Telegram, or a web dashboard — powered by Claude AI and integrated into their workflow via OpenClaw.

Three specialist AI agents handle distinct domains:

- **Interaction Safety Agent** — cross-references a patient's active prescriptions against a new medication before dispensing. Crucially, risk ratings are anchored to a deterministic clinical rules table: the AI cannot downgrade a HIGH interaction to MODERATE. This is a deliberate safety design choice — AI reasoning enriches the output, but cannot weaken a known contraindication.
- **Stock Intelligence Agent** — reviews inventory levels, flags near-expiry medications, calculates waste cost, and triggers supplier reorders automatically.
- **Patient Engagement Agent** — generates personalised SMS/email refill reminders for patients due within a configurable window, using each patient's name and specific medication history rather than a generic template.

An Orchestrator Agent sits above all three, accepting plain English from the pharmacist and coordinating whichever agents are needed — so "Good morning, run the daily check" triggers a full stock review and patient outreach in a single message.

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
   ┌────┴───────────────────────────┐
   │                                │
   ▼                                ▼
Tool Layer (deterministic)     Agent Layer (Claude Haiku)
- DB queries                   - OrchestratorAgent (agentic loop)
- Stock checks                 - InteractionSafetyAgent
- Audit logging                - StockIntelligenceAgent
- Message dispatch             - PatientEngagementAgent
```

The tool/agent separation is intentional. Every database query, reorder, and message is handled by deterministic Python functions — auditable, testable, and replaceable. Claude only touches the reasoning layer: interpreting intent, weighing clinical risk, and generating human-readable output.

## Key safety decisions

1. **Deterministic interaction rules** — 40+ clinically validated drug pairs with fixed severity levels injected into every interaction check. Claude reasons around them; it cannot override them.
2. **Human-in-the-loop** — every agent recommendation requires pharmacist sign-off before clinical action is taken. The system advises; it does not dispense.
3. **Full audit trail** — every agent action is logged to a timestamped `AuditLog` table with agent identity and patient reference. Designed for NHS Scotland regulatory compliance.
4. **CHI number validation** — Scottish CHI numbers are validated against the Modulus 11 algorithm before any patient query reaches the database.
5. **Data residency** — designed for deployment within DataVita's Scottish data centres, keeping patient data within Scotland per NHS Scotland GDPR requirements.

## OpenClaw integration

Four skills connect PharmAgent to any chat app via OpenClaw:

| Skill | Trigger |
|---|---|
| `pharmagent-morning-briefing` | "Run the daily pharmacy check" |
| `pharmagent-interaction-check` | "Check CHI 1203480016 for Ibuprofen" |
| `pharmagent-stock-review` | "What's running low?" |
| `pharmagent-patient-engagement` | "Send refill reminders this week" |

The daily briefing skill can be scheduled as a cron task in OpenClaw, delivering an automated 08:00 weekday briefing to the pharmacist's phone.

> **Note for judges running locally:** The SKILL.md files point to the Railway deployment URL. If self-hosting, update the base URL in each skill file or set the `PHARMAGENT_API_URL` environment variable.

## Dashboard

The web dashboard demonstrates the full system in one place:

- **Daily Briefing card** — single button triggers all three agents via the Orchestrator and returns a unified NHS-style clinical report. Downloadable as PDF.
- **Drug Interaction Checker** — patient CHI + new medication → structured risk report with severity, mechanism, and dispensing recommendation. Quick-fill demo chips for instant testing.
- **Stock Review** — AI analysis with low-stock and expiry alerts, inline reorder buttons.
- **Patient Lookup** — full medication profile by CHI number.
- **Patient Engagement** — personalised SMS/email reminder campaigns by type (refill, seasonal, flu vaccination, etc.).
- **Audit Log** — live table of all agent actions, satisfying NFR-04 visibility. Every interaction check, stock review, and patient message is logged with timestamp, agent identity, and detail.

## Live demo

| | |
|---|---|
| **Dashboard** | https://web-production-1f27a.up.railway.app/static/dashboard.html |
| **API docs** | https://web-production-1f27a.up.railway.app/docs |
| **Health** | https://web-production-1f27a.up.railway.app/health |

All 10 demo patients are seeded. Quick-fill buttons in the dashboard auto-populate the forms — no CHI number memorisation needed. Full list:

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
