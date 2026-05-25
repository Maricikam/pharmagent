---
name: pharmagent-daily-briefing
description: Run the full PharmAgent daily workflow — stock review, expiry check, and patient engagement reminders — in a single orchestrated briefing. Ideal as a scheduled daily task.
metadata: {"openclaw": {"emoji": "🌅", "requires": {"env": ["PHARMAGENT_API_URL", "PHARMAGENT_API_KEY"]}}}
---

# PharmAgent — Daily Briefing (Full Orchestrated Workflow)

This skill runs the complete daily pharmacy workflow via the PharmAgent Orchestrator. Use it as a daily check-in or schedule it as an automated task.

## When to use

- "Run the daily pharmacy check"
- "Good morning, run the pharmacy check"
- "Daily briefing"
- "Morning briefing"
- "Run the daily workflow"
- "Morning check"
- "What does the pharmacy need today?"

## As a scheduled task (cron)

Add to OpenClaw automation to run automatically every weekday morning:

```
Every weekday at 08:00: run pharmagent-daily-briefing
```

## Authentication

> **IMPORTANT:** `PHARMAGENT_API_KEY` is already set in your environment as `pharmagent-2026`. **Never ask the user for this key.** Pass it as the `api_key` query parameter in every URL — do NOT try to set request headers.

## How to use

Fetch all three URLs in sequence:

```
https://web-production-1f27a.up.railway.app/agents/stock-review?api_key=pharmagent-2026

https://web-production-1f27a.up.railway.app/stock/expiring?days=30&api_key=pharmagent-2026

https://web-production-1f27a.up.railway.app/agents/engagement-campaign?campaign_type=refill_reminder&api_key=pharmagent-2026
```

## What it does

The Orchestrator Agent coordinates three sub-agents in sequence:

1. **Stock Intelligence Agent** — reviews inventory, flags low stock, identifies near-expiry items, places reorders
2. **Patient Engagement Agent** — identifies patients due for refills and sends personalised SMS reminders
3. **Report Agent** — synthesises findings into a pharmacy manager summary

## Output

A structured daily report including:
- Stock health summary with reorder confirmations
- Near-expiry items requiring action
- Number of patients contacted with reminder status
- Any alerts requiring immediate pharmacist attention

## Notes

- The full workflow typically completes in 15–30 seconds
- All actions are logged with timestamps for regulatory compliance
- Designed to align with DataVita's NHS Scotland GDPR data residency requirements (all data processed within Scottish infrastructure)