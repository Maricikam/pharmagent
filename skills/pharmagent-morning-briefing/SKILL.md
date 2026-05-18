---
name: pharmagent-morning-briefing
description: Run the full PharmAgent morning workflow — stock review, expiry check, and patient engagement reminders — in a single orchestrated briefing. Ideal as a scheduled daily task.
homepage: https://github.com/Maricikam/pharmagent
metadata: {"openclaw": {"emoji": "🌅", "requires": {"env": ["PHARMAGENT_API_URL"]}}}
---

# PharmAgent — Morning Briefing (Full Orchestrated Workflow)

This skill runs the complete daily pharmacy startup workflow via the PharmAgent Orchestrator. Use it as a morning check-in or schedule it as a daily automated task.

## When to use

- "Good morning, run the pharmacy check"
- "Morning briefing"
- "Run the daily workflow"
- "What does the pharmacy need today?"

## As a scheduled task (cron)

Add to OpenClaw automation to run automatically every weekday morning:

```
Every weekday at 08:00: run pharmagent-morning-briefing
```

## How to use

```
POST ${PHARMAGENT_API_URL}/agents/orchestrate
Content-Type: application/json

{
  "intent": "Good morning. Please do a full stock review, flag anything expiring in the next 30 days, and send SMS reminders to patients whose prescriptions are due in the next 7 days."
}
```

## What it does

The Orchestrator Agent coordinates three sub-agents in sequence:

1. **Stock Intelligence Agent** — reviews inventory, flags low stock, identifies near-expiry items, places reorders
2. **Patient Engagement Agent** — identifies patients due for refills and sends personalised SMS reminders
3. **Report Agent** — synthesises findings into a pharmacy manager summary

## Output

A structured morning report including:
- Stock health summary with reorder confirmations
- Near-expiry items requiring action
- Number of patients contacted with reminder status
- Any alerts requiring immediate pharmacist attention

## Notes

- The full workflow typically completes in 15–30 seconds
- All actions are logged with timestamps for regulatory compliance
- Designed to align with DataVita's NHS Scotland GDPR data residency requirements (all data processed within Scottish infrastructure)