---
name: pharmagent-morning-briefing
description: Run the full PharmAgent morning/daily workflow — stock review, expiry check, and patient engagement reminders. Alias for pharmagent-daily-briefing.
homepage: https://github.com/Maricikam/pharmagent
metadata: {"openclaw": {"emoji": "🌅", "requires": {"env": ["PHARMAGENT_API_URL", "PHARMAGENT_API_KEY"]}}}
---

# PharmAgent — Morning / Daily Briefing

Use this skill for any morning check, daily pharmacy check, or daily briefing request.

## When to use

- "Run the daily pharmacy check"
- "Morning check"
- "Good morning, run the check"
- "Daily briefing"
- "Run the morning briefing"
- "What does the pharmacy need today?"

## Authentication

Every request must include the API key header — without it the server returns 401.

> **IMPORTANT:** `PHARMAGENT_API_KEY` is already configured in your environment. Read it from the `$PHARMAGENT_API_KEY` environment variable and pass it as the `X-API-Key` header in **every** request. **Never ask the user for this key** — it is pre-configured and the user should not need to provide it.

## How to use

Run all three agent steps in sequence. For each request, pass `X-API-Key` set to the value of `$PHARMAGENT_API_KEY`:

```
GET https://web-production-1f27a.up.railway.app/agents/stock-review
X-API-Key: <value of $PHARMAGENT_API_KEY>

GET https://web-production-1f27a.up.railway.app/stock/expiring?days=30
X-API-Key: <value of $PHARMAGENT_API_KEY>

GET https://web-production-1f27a.up.railway.app/agents/engagement-campaign?campaign_type=refill_reminder
X-API-Key: <value of $PHARMAGENT_API_KEY>
```

## What it does

1. **Stock Intelligence Agent** — reviews inventory, flags low stock, identifies near-expiry items, places reorders
2. **Patient Engagement Agent** — identifies patients due for refills and sends personalised SMS reminders
3. Synthesises findings into a pharmacy manager summary

## Output

A structured daily report including:
- Stock health summary with reorder confirmations
- Near-expiry items requiring action
- Number of patients contacted with reminder status
- Any alerts requiring immediate pharmacist attention

## Notes

- All actions are logged with timestamps for regulatory compliance
- The full workflow typically completes in 15–30 seconds
