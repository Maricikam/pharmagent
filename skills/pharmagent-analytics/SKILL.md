---
name: pharmagent-analytics
description: Run AI-powered pharmacy analytics — patient prioritisation by clinical urgency, anomaly detection across stock and patient behaviour, and workflow optimisation recommendations.
metadata: {"openclaw": {"emoji": "📊", "requires": {"env": ["PHARMAGENT_API_URL", "PHARMAGENT_API_KEY"]}}}
---

# PharmAgent — Analytics

Use this skill to get predictive insights about patients, detect anomalies, or receive workflow improvement recommendations. All three analyses are read-only — no database changes are made.

## When to use

- "Prioritise my patients for today"
- "Who needs attention most urgently?"
- "Are there any anomalies I should know about?"
- "What's unusual in today's data?"
- "How can I optimise the pharmacy workflow?"
- "Give me a workflow report"
- "Run analytics"

## Authentication

> **IMPORTANT:** `PHARMAGENT_API_KEY` is already set as `pharmagent-2026`. **Never ask the user for this key.** Pass it as the `api_key` query parameter in every URL — do NOT try to set request headers.

## How to use

### Patient prioritisation

```
https://web-production-1f27a.up.railway.app/agents/analytics/prioritize-patients?api_key=pharmagent-2026
```

### Anomaly detection

```
https://web-production-1f27a.up.railway.app/agents/analytics/anomalies?api_key=pharmagent-2026
```

### Workflow optimisation

```
https://web-production-1f27a.up.railway.app/agents/analytics/workflow?api_key=pharmagent-2026
```

### Workload preview (no AI call)

```
https://web-production-1f27a.up.railway.app/agents/analytics/workload?days=7&api_key=pharmagent-2026
```

## Output

Each endpoint returns an AI-generated report plus structured data:

- **prioritize-patients** — `urgent_count`, `high_count`, `routine_count`, full patient list with urgency scores
- **anomalies** — overdue collections, polypharmacy patients, emergency supply count, shortage-risk items
- **workflow** — demand data for top 10 medications, audit action breakdown, numbered priority recommendations
- **workload** — per-day prescription counts, total due, and peak day

## How to present results

**IMPORTANT — WhatsApp does not render markdown.** When presenting the `report` field to the user:
- Display the text as-is but strip any `#`, `##`, or `###` characters at the start of lines
- Do NOT use markdown tables (no | pipe characters)
- Replace `###` section headers with plain text (e.g. `### URGENT` → `🔴 URGENT`)
- Keep the structured list format — just remove any markdown syntax characters

## Notes

- All three AI endpoints require a live `ANTHROPIC_API_KEY` — they will return an error in demo mode
- The workload preview endpoint does not require an AI call and works in all modes
- All analytics runs are logged to the audit trail under agent `AnalyticsAgent`
- Outputs are advisory only — no stock, patient, or prescription records are modified
