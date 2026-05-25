---
name: pharmagent-handover
description: Generate a shift handover briefing for the incoming pharmacist. Combines recent audit activity, stock alerts, and urgent patient refills into a structured NHS clinical handover note.
metadata: {"openclaw": {"emoji": "📋", "requires": {"env": ["PHARMAGENT_API_URL", "PHARMAGENT_API_KEY"]}}}
---

# PharmAgent — Shift Handover

Use this skill at the end of a shift to generate a structured handover note for the incoming pharmacist.

## When to use

- "Generate handover notes"
- "End of shift summary"
- "What does the next shift need to know?"
- "Handover briefing"

## Authentication

> **IMPORTANT:** `PHARMAGENT_API_KEY` is already set as `pharmagent-2026`. **Never ask the user for this key.** Pass it as the `api_key` query parameter in the URL — do NOT try to set request headers.

## How to use

```
https://web-production-1f27a.up.railway.app/agents/handover?api_key=pharmagent-2026
```

No parameters required.

## What it includes

The handover note covers:

1. **Handover Summary** — overall pharmacy status for the shift
2. **Pending Actions** — anything started this shift that needs follow-up
3. **Stock Alerts** — critical low stock or expiring items needing action
4. **Patients to Watch** — patients due for urgent refills in the next 3 days
5. **Recent Interactions Flagged** — any HIGH-risk checks from this shift
6. **Notes for Next Shift** — anything else the incoming pharmacist needs to know

## Output

Returns a structured clinical handover document in NHS format, plus a summary of:
- Number of actions taken this shift
- Low stock items
- Expiring items within 14 days
- Patients due for urgent refill

## Notes

- Draws from the last 12 hours of audit log activity
- All handover generation is itself logged to the audit trail
- Designed for end-of-shift use; run before handing over keys
