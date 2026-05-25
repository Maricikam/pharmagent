"""
Emergency Supply Agent — PharmAgent AI
========================================
Processes emergency medication supply requests. Generates a legally
formatted emergency supply record for NHS Scotland regulatory compliance,
runs an interaction check against the patient's active medications,
and logs to the audit trail.

Legal basis: Medicines (Pharmacy and General Sale—Exemption) Order 1980,
as amended. Pharmacy (Scotland) Act 2011. Records must be retained for
2 years; prescriber must be notified within 72 hours of supply.
"""

import anthropic
from datetime import datetime, timedelta
from tools.pharmacy_tools import (
    get_patient_by_nhs, get_patient_by_name,
    get_active_prescriptions, log_audit_event,
)
from agents.interaction_safety_agent import check_interactions
from config import MODEL

SYSTEM_PROMPT = """You are generating an emergency supply record for a Scottish community pharmacy.

Format as a formal NHS pharmacy document. No emojis. Plain text only.
Use DD/MM/YYYY dates and 24-hour time.

Structure the document exactly as follows:

EMERGENCY SUPPLY RECORD
=======================
Date/Time:
Patient:
CHI Number:
Date of Birth:

Medication Supplied:
Strength/Form:
Quantity:

Reason for Emergency Supply:
Prescriber Contacted: [Yes/No + outcome, or reason if not contacted]

Interaction Check:
[Brief summary of the interaction check result provided]

Pharmacist Action and Counselling:
[What the pharmacist should tell the patient — specific to this medication]

Follow-up Required:
[What must happen next — e.g. patient to contact GP within 72 hours]

---
REGULATORY NOTE
[One paragraph reminding the pharmacist of their legal obligations under
NHS Scotland: notification to prescriber, record retention for 2 years,
CDR requirements if applicable]

Be precise and formal. This is a legal document."""


def _local_now():
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("Europe/London"))
    except Exception:
        return datetime.utcnow() + timedelta(hours=1)


def process_emergency_supply(
    medication: str,
    quantity: int,
    reason: str,
    nhs_number: str = None,
    patient_name: str = None,
    prescriber_contacted: bool = False,
) -> dict:
    """
    Process an emergency supply request.

    Resolves patient by CHI or name, runs an interaction check,
    generates a legal supply record, and logs to the audit trail.
    """
    client = anthropic.Anthropic()

    # ── Resolve patient ───────────────────────────────────────────────────────
    patient = None

    if nhs_number:
        candidate = get_patient_by_nhs(nhs_number)
        if "error" not in candidate:
            patient = candidate

    if patient is None and patient_name:
        matches = get_patient_by_name(patient_name)
        if len(matches) == 1:
            nhs_number = matches[0]["nhs_number"]
            patient = get_patient_by_nhs(nhs_number)
            if "error" in patient:
                patient = None
        elif len(matches) > 1:
            return {
                "error": "multiple_patients",
                "message": (
                    f"Multiple patients match '{patient_name}'. "
                    "Please provide the CHI number to proceed."
                ),
                "matches": [
                    {"name": m["name"], "nhs_number": m["nhs_number"],
                     "dob": m["date_of_birth"]}
                    for m in matches
                ],
            }

    # ── Interaction check ─────────────────────────────────────────────────────
    interaction_summary = "No patient record found — interaction check not performed."
    if patient:
        prescriptions = get_active_prescriptions(patient["id"])
        if prescriptions:
            full_result = check_interactions(
                nhs_number,
                new_medication=medication,
                _patient=patient,
                _prescriptions=prescriptions,
            )
            # Extract the key recommendation lines for the supply record
            lines = full_result["text"].split("\n")
            key_lines = [
                l.strip() for l in lines
                if any(k in l.upper() for k in
                       ["HIGH", "MODERATE", "LOW", "SAFE", "DO NOT",
                        "PHARMACIST", "RECOMMENDATION", "STATUS"])
                and l.strip()
            ]
            interaction_summary = " | ".join(key_lines[:4]) if key_lines else full_result[:250]
        else:
            interaction_summary = "No active prescriptions on record — no interaction check required."

    # ── Build prompt context ──────────────────────────────────────────────────
    now = _local_now()

    patient_name_str = patient["name"] if patient else (patient_name or "Unknown")
    chi_str = nhs_number or "Not provided"
    dob_str = patient["date_of_birth"] if patient else "Unknown"

    context = f"""Date/Time: {now.strftime('%d/%m/%Y  %H:%M')} BST
Patient: {patient_name_str}
CHI Number: {chi_str}
Date of Birth: {dob_str}
Medication: {medication}
Quantity: {quantity} {'unit' if quantity == 1 else 'units'}
Reason for emergency supply: {reason}
Prescriber contacted: {'Yes' if prescriber_contacted else 'No'}

Interaction check result:
{interaction_summary}

Generate the emergency supply record.
"""

    response = client.messages.create(
        model=MODEL,
        max_tokens=800,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": context}],
    )

    record = response.content[0].text

    log_audit_event(
        agent="EmergencySupplyAgent",
        action="EMERGENCY_SUPPLY",
        details=(
            f"Patient: {patient_name_str} (CHI: {chi_str}) | "
            f"Med: {medication} x{quantity} | "
            f"Reason: {reason[:80]}"
        ),
        patient_id=patient.get("id") if patient else None,
    )

    return {
        "generated_at": now.strftime("%d/%m/%Y  %H:%M"),
        "patient": patient_name_str,
        "nhs_number": chi_str,
        "medication": medication,
        "quantity": quantity,
        "interaction_check": interaction_summary,
        "record": record,
    }


if __name__ == "__main__":
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    print("=== Emergency Supply Agent ===\n")
    result = process_emergency_supply(
        medication="Warfarin 5mg",
        quantity=7,
        reason="Patient ran out over the weekend, unable to reach GP",
        patient_name="Thomas Robertson",
        prescriber_contacted=False,
    )
    if "error" in result:
        print(f"Error: {result['message']}")
    else:
        print(f"Patient: {result['patient']} | Med: {result['medication']} x{result['quantity']}")
        print(f"Interaction: {result['interaction_check'][:120]}\n")
        print(result["record"])
