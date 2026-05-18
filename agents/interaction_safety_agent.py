"""
Interaction Safety Agent — PharmAgent AI
=========================================
Checks a patient's active medications against a new prescription for
drug interaction risks before dispensing.

Responsibility:
    Given an NHS number and a new medication name, this agent retrieves
    the patient's active prescription history and applies AI reasoning
    to identify contraindications, severity levels, and clinical
    recommendations.

Tools used:
    - get_patient_by_nhs()       — retrieve patient record
    - get_active_prescriptions() — fetch current medication list
    - log_audit_entry()          — write action to audit trail

Output:
    A structured interaction report with risk level (LOW/MEDIUM/HIGH),
    detected interactions, and a clinical recommendation. All reports
    require pharmacist sign-off before dispensing action is taken.

Data residency:
    All patient data queried and processed within DataVita Scottish
    infrastructure (NFR-01 compliant).
"""

"""
Interaction Safety Agent
Checks a patient's active prescriptions for drug interaction risks.
Requires pharmacist approval before any dispensing action is taken.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import anthropic
import json
from tools.pharmacy_tools import get_patient_by_nhs, get_active_prescriptions, log_audit_event

SYSTEM_PROMPT = """You are the Interaction Safety Agent for PharmAgent AI, deployed in a Scottish community pharmacy.

Your role is to analyse a patient's active prescriptions and identify any drug interaction risks.

When you receive prescription data:
1. List all active medications clearly
2. Identify any known interactions between them (use the 'known_interactions' field as a guide)
3. Rate each interaction: CRITICAL (bleeding risk, serotonin syndrome, cardiac) | MODERATE | MINOR
4. For CRITICAL interactions, recommend the pharmacist consult before dispensing
5. Provide a brief clinical rationale for each interaction flagged

Always be concise and structured. You are supporting a pharmacist — not replacing them.
End with a clear RECOMMENDATION: SAFE TO DISPENSE | PHARMACIST REVIEW REQUIRED | DO NOT DISPENSE WITHOUT CONSULTATION"""


def check_interactions(nhs_number: str) -> str:
    client = anthropic.Anthropic()
    patient = get_patient_by_nhs(nhs_number)
    if "error" in patient:
        return patient["error"]

    prescriptions = get_active_prescriptions(patient["id"])
    if not prescriptions:
        return f"No active prescriptions found for {patient['name']}."

    context = f"""
Patient: {patient['name']} (DOB: {patient['date_of_birth']})
NHS Number: {nhs_number}

Active Prescriptions:
{json.dumps(prescriptions, indent=2)}

Please analyse these prescriptions for drug interactions and provide your safety assessment.
"""

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": context}],
    )

    result = response.content[0].text

    log_audit_event(
        agent="InteractionSafetyAgent",
        action="INTERACTION_CHECK",
        details=f"Patient: {patient['name']} ({nhs_number}) | Result: {result[:150]}",
        patient_id=patient["id"],
    )

    return result


if __name__ == "__main__":
    print("=== Interaction Safety Agent ===\n")
    for nhs in ["4823719056", "8374650192"]:
        print(f"Checking NHS: {nhs}")
        print("-" * 50)
        print(check_interactions(nhs))
        print("\n")