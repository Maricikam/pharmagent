---
name: pharmagent-patient-profile
description: Look up a patient's full active medication profile by name or CHI number. Returns all current prescriptions, dosages, and prescribers.
homepage: https://github.com/Maricikam/pharmagent
metadata: {"openclaw": {"emoji": "👤", "requires": {"env": ["PHARMAGENT_API_URL", "PHARMAGENT_API_KEY"]}}}
---

# PharmAgent — Patient Profile

Use this skill to look up what a patient is currently prescribed, without running a full interaction check.

## When to use

- "What is Margaret Campbell on?"
- "Show me the medications for CHI 1203480016"
- "What's Thomas Robertson's prescription list?"
- "Pull up the profile for patient Robertson"

## How to use

### By CHI number

```
GET https://web-production-1f27a.up.railway.app/agents/patient-profile?nhs_number=1203480016
```

### By patient name

```
GET https://web-production-1f27a.up.railway.app/agents/patient-profile?name=Margaret%20Campbell
```

**Parameters:**
- `nhs_number` (string, optional) — patient's 10-digit CHI number
- `name` (string, optional) — patient name or partial name; if multiple patients match, a list is returned for clarification

At least one parameter is required.

## Output

Returns:
- Patient name, CHI number, date of birth
- Full list of active prescriptions with dosage, frequency, and prescribing doctor
- Total prescription count

## Notes

- If a name matches multiple patients, the skill returns the list and asks for clarification
- All lookups are logged to the audit trail
- Patient data is processed within DataVita Scottish infrastructure (NHS GDPR compliant)
