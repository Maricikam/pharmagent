---
name: pharmagent-emergency-supply
description: Process an emergency medication supply request. Runs an interaction check, generates a legally formatted NHS Scotland supply record, and logs to the audit trail.
homepage: https://github.com/Maricikam/pharmagent
metadata: {"openclaw": {"emoji": "🚨", "requires": {"env": ["PHARMAGENT_API_URL", "PHARMAGENT_API_KEY"]}}}
---

# PharmAgent — Emergency Supply

Use this skill when a patient has run out of medication and cannot reach their GP. Generates a legal emergency supply record compliant with NHS Scotland requirements.

## When to use

- "Emergency supply for Thomas Robertson — he's run out of Warfarin"
- "Patient needs emergency supply of Metformin 500mg, 7 days' worth"
- "Log an emergency supply — patient can't reach their doctor"

## Authentication

Every request must include the API key header — without it the server returns 401:

```
X-API-Key: $PHARMAGENT_API_KEY
```

## How to use

```
POST https://web-production-1f27a.up.railway.app/agents/emergency-supply
Content-Type: application/json
X-API-Key: $PHARMAGENT_API_KEY

{
  "medication": "Warfarin 5mg",
  "quantity": 7,
  "reason": "Patient ran out over the weekend, GP surgery closed",
  "patient_name": "Thomas Robertson",
  "prescriber_contacted": false
}
```

Or by CHI number:

```json
{
  "medication": "Warfarin 5mg",
  "quantity": 7,
  "reason": "Patient ran out over the weekend",
  "nhs_number": "2201380015",
  "prescriber_contacted": false
}
```

**Parameters:**
- `medication` (string, required) — medication name and strength
- `quantity` (integer, required) — number of units to supply
- `reason` (string, required) — reason for emergency supply
- `nhs_number` (string, optional) — patient's CHI number
- `patient_name` (string, optional) — patient name (resolved via lookup if CHI not provided)
- `prescriber_contacted` (boolean, default false) — whether prescriber was contacted

At least one of `nhs_number` or `patient_name` is required.

## What it does

1. Resolves the patient by name or CHI number
2. Runs a drug interaction check against their active prescriptions
3. Generates a formal emergency supply record with all legally required fields
4. Logs the supply to the audit trail with action type `EMERGENCY_SUPPLY`

## Output

Returns:
- Formatted emergency supply record (ready to print or file)
- Interaction check summary for the supplied medication
- Regulatory note reminding the pharmacist of NHS Scotland obligations

## Legal notes

- Pharmacist must notify the prescriber within 72 hours of supply
- Record must be retained for 2 years per NHS Scotland requirements
- This record does not replace the pharmacist's professional judgement
- All entries are logged with timestamp and pharmacist reference for regulatory compliance
