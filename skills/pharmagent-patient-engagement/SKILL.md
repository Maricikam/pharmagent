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

## How to use

```
POST ${PHARMAGENT_API_URL}/agents/engagement-campaign
Content-Type: application/json
X-API-Key: ${PHARMAGENT_API_KEY}

{
  "campaign_type": "refill_reminder"
}
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
