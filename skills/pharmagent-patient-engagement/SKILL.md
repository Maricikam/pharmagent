---
name: pharmagent-patient-engagement
description: Send personalised SMS or email refill reminders to patients whose prescriptions are due soon. Filters by days ahead and channel.
metadata: {"openclaw": {"emoji": "📱", "requires": {"env": ["PHARMAGENT_API_URL", "PHARMAGENT_API_KEY"]}}}
---

# PharmAgent — Patient Engagement

Use this skill to send proactive refill reminders to patients, or to check who needs to be contacted about upcoming prescriptions.

## When to use

- "Send refill reminders"
- "Who needs to be reminded about their medication this week?"
- "Contact patients whose prescriptions are due in the next 7 days"
- "Run the engagement campaign"
- "Send SMS reminders to patients"

## Authentication

> **IMPORTANT:** `PHARMAGENT_API_KEY` is already set as `pharmagent-2026`. **Never ask the user for this key.** Pass it as the `api_key` query parameter — do NOT try to set request headers.

## How to use

```
https://web-production-1f27a.up.railway.app/agents/engagement-campaign?campaign_type=refill_reminder&api_key=pharmagent-2026
```

Other campaign types:
```
https://web-production-1f27a.up.railway.app/agents/engagement-campaign?campaign_type=adherence_check&api_key=pharmagent-2026

https://web-production-1f27a.up.railway.app/agents/engagement-campaign?campaign_type=seasonal&api_key=pharmagent-2026
```

**Parameters:**
- `campaign_type` (string, default `"refill_reminder"`) — one of `"refill_reminder"`, `"adherence_check"`, or `"seasonal"`

## Output

Returns:
- Number of patients contacted
- Per-patient personalised message previews
- Delivery status for each message
- Patients skipped (opted out or recently contacted)

## How to present results

**IMPORTANT — WhatsApp does not render markdown.** When summarising the API response, follow this exact format:

```
✅ Refill Reminders Sent — This Week

4 patients contacted via SMS:

1. Margaret Campbell (78) — Warfarin 5mg, Aspirin 75mg — due in 5 days — Sent
2. James Morrison (70) — Clarithromycin 500mg — due in 2 days — Sent
3. Patricia Henderson (63) — Lisinopril 10mg, Spironolactone 25mg — due in 7 days — Sent
4. Dorothy Reid (59) — Alendronic Acid 70mg — due in 5 days — Sent

Key alerts:
• 🔴 Margaret Campbell — elderly patient, HIGH non-adherence risk
• James Morrison — urgent (due in 2 days)

All patients received personalised SMS with pharmacy contact: 0141 555 0199
```

Rules:
- Use a numbered list, NOT a markdown table (no | pipe characters)
- Do NOT use ## or ### headers — use plain text with an emoji prefix for section titles
- Each patient on ONE line: Number. Name (age) — Medications — due in X days — Status
- Keep it compact — one line per patient

## Notes

- Messages are personalised using each patient's medication history and name
- Patients who have opted out of communications are automatically excluded
- All messages are logged in the audit trail
- In production, real SMS delivery uses Twilio / NHS Notify; in demo mode, messages are simulated and logged
