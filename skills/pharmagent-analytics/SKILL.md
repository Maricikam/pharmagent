---
name: pharmagent-analytics
description: Run AI-powered pharmacy analytics — patient prioritisation by clinical urgency, anomaly detection across stock and patient behaviour, and workflow optimisation recommendations.
homepage: https://github.com/Maricikam/pharmagent
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

Every request must include the API key header — without it the server returns 401.

> **IMPORTANT:** `PHARMAGENT_API_KEY` is already configured in your environment. Read it from the `$PHARMAGENT_API_KEY` environment variable and pass it as the `X-API-Key` header in **every** request. **Never ask the user for this key** — it is pre-configured and the user should not need to provide it.

## How to use

For every request below, pass `X-API-Key` set to the value of `$PHARMAGENT_API_KEY`.

### Patient prioritisation

Scores every active patient by clinical urgency (overdue collection, adherence risk, polypharmacy) and returns a ranked action list grouped as `[URGENT]`, `[HIGH]`, `[ROUTINE]`.

```
GET https://web-production-1f27a.up.railway.app/agents/analytics/prioritize-patients
X-API-Key: <value of $PHARMAGENT_API_KEY>
```

### Anomaly detection

Identifies unusual patterns across stock demand, patient collections, and audit activity. Flags findings as `[CRITICAL]`, `[WARNING]`, or `[ADVISORY]`.

```
GET https://web-production-1f27a.up.railway.app/agents/analytics/anomalies
X-API-Key: <value of $PHARMAGENT_API_KEY>
```

### Workflow optimisation

Analyses recent audit history and patient load to generate workflow improvement recommendations, each tagged `[IMMEDIATE]`, `[THIS WEEK]`, or `[NEXT MONTH]`.

```
GET https://web-production-1f27a.up.railway.app/agents/analytics/workflow
X-API-Key: <value of $PHARMAGENT_API_KEY>
```

### Workload preview (no AI call)

Returns prescription counts due per day for the next N days — useful for staffing and planning.

```
GET https://web-production-1f27a.up.railway.app/agents/analytics/workload?days=7
X-API-Key: <value of $PHARMAGENT_API_KEY>
```

## Output

Each endpoint returns an AI-generated report plus structured data:

- **prioritize-patients** — `urgent_count`, `high_count`, `routine_count`, full patient list with urgency scores
- **anomalies** — overdue collections, polypharmacy patients, emergency supply count, shortage-risk items
- **workflow** — demand data for top 10 medications, audit action breakdown, numbered priority recommendations
- **workload** — per-day prescription counts, total due, and peak day

## Notes

- All three AI endpoints require a live `ANTHROPIC_API_KEY` — they will return an error in demo mode
- The workload preview endpoint does not require an AI call and works in all modes
- All analytics runs are logged to the audit trail under agent `AnalyticsAgent`
- Outputs are advisory only — no stock, patient, or prescription records are modified
