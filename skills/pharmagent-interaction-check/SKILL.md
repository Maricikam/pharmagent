---
name: pharmagent-interaction-check
description: Check a patient's active medications against a new prescription for drug interaction risks. Requires a CHI number and the name of the new medication.
metadata: {"openclaw": {"emoji": "🛡️", "requires": {"env": ["PHARMAGENT_API_URL", "PHARMAGENT_API_KEY"]}}}
---

# PharmAgent — Drug Interaction Checker

Use this skill before dispensing a new medication to check for interactions with a patient's existing prescriptions.

## When to use

- "Check [patient CHI] before I dispense [medication]"
- "Is it safe to give Ibuprofen to patient 1203480016?"
- "Run an interaction check"
- "Check medications for CHI number 1203480016"

## Authentication

> **IMPORTANT:** `PHARMAGENT_API_KEY` is already set as `pharmagent-2026`. **Never ask the user for this key.** Pass it as the `api_key` query parameter — do NOT try to set request headers.

## How to use

```
https://web-production-1f27a.up.railway.app/agents/interaction-check?nhs_number=<CHI>&new_medication_name=<medication>&api_key=pharmagent-2026
```

Example:
```
https://web-production-1f27a.up.railway.app/agents/interaction-check?nhs_number=1203480016&new_medication_name=Ibuprofen&api_key=pharmagent-2026
```

**Parameters:**
- `nhs_number` (string, required) — patient's 10-digit CHI number
- `new_medication_name` (string, required) — name of the new medication to check (e.g. "Ibuprofen 400mg")

## Output

Returns a structured interaction report including:
- Patient name and date of birth
- Full list of active medications
- Interaction risk level: HIGH / MODERATE / LOW
- Detected interactions with severity and clinical rationale
- Pharmacist recommendation (safe to dispense / review required / do not dispense)
- Audit reference number and timestamp

## Notes

- All HIGH-risk interactions require pharmacist sign-off before dispensing
- Risk levels are anchored to a deterministic clinical rules table — the AI cannot downgrade a HIGH rating
- All checks are logged to the audit trail with a reference number
- Patient data is processed within DataVita Scottish infrastructure (NHS GDPR compliant)
