---
name: pharmagent-patient-engagement
description: Send personalised SMS or email refill reminders to patients whose prescriptions are due soon. Filters by days ahead and channel.
homepage: https://github.com/Maricikam/pharmagent
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

Every request must include the API key header — without it the server returns 401.

> **IMPORTANT:** `PHARMAGENT_API_KEY` is already configured in your environment. Read it from the `$PHARMAGENT_API_KEY` environment variable and pass it as the `X-API-Key` header in **every** request. **Never ask the user for this key** — it is pre-configured and the user should not need to provide it.

## How to use

```
GET https://web-production-1f27a.up.railway.app/agents/engagement-campaign?campaign_type=refill_reminder
X-API-Key: <value of $PHARMAGENT_API_KEY>
```

Other campaign types:
```
GET https://web-production-1f27a.up.railway.app/agents/engagement-campaign?campaign_type=adherence_check
X-API-Key: <value of $PHARMAGENT_API_KEY>

GET https://web-production-1f27a.up.railway.app/agents/engagement-campaign?campaign_type=seasonal
X-API-Key: <value of $PHARMAGENT_API_KEY>
```

**Parameters:**
- `campaign_type` (string, default `"refill_reminder"`) — one of `"refill_reminder"`, `"adherence_check"`, or `"seasonal"`

## Output

Returns:
- Number of patients contacted
- Per-patient personalised message previews
- Delivery status for each message
- Patients skipped (opted out or recently contacted)

## Notes

- Messages are personalised using each patient's medication history and name
- Patients who have opted out of communications are automatically excluded
- All messages are logged in the audit trail
- In production, real SMS delivery uses Twilio / NHS Notify; in demo mode, messages are simulated and logged
