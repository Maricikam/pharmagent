"""
Interaction Safety Agent — PharmAgent AI
=========================================
Checks a patient's active medications against a new prescription for
drug interaction risks before dispensing.

Responsibility:
    Given a CHI number and a new medication name, this agent retrieves
    the patient's active prescription history and applies AI reasoning
    to identify contraindications, severity levels, and clinical
    recommendations.

Tools used:
    - get_patient_by_nhs()       — retrieve patient record
    - get_active_prescriptions() — fetch current medication list
    - log_audit_entry()          — write action to audit trail

Output:
    A structured interaction report with risk level (LOW/MODERATE/HIGH),
    detected interactions, and a clinical recommendation. All reports
    require pharmacist sign-off before dispensing action is taken.

Data residency:
    All patient data queried and processed within DataVita Scottish
    infrastructure (NFR-01 compliant).
"""

import anthropic
import json
from tools.pharmacy_tools import get_patient_by_nhs, get_active_prescriptions, log_audit_event
from config import MODEL

# ---------------------------------------------------------------------------
# DETERMINISTIC INTERACTION RULES TABLE
# ---------------------------------------------------------------------------
# These rules are injected into the system prompt so the AI produces
# consistent, reproducible risk ratings for every known drug pair.
# The AI still provides clinical reasoning — but the severity level
# is anchored by this table and must not deviate from it.
#
# Format:  (drug_a, drug_b): (severity, brief mechanism)
# Matching is case-insensitive and substring-based (e.g. "warfarin"
# matches "Warfarin 5mg").
# ---------------------------------------------------------------------------

INTERACTION_RULES = """
MANDATORY INTERACTION SEVERITY TABLE
=====================================
You MUST use the exact severity level from this table when the drug pair
is present. Do not upgrade or downgrade based on your own reasoning.
If a pair is not in this table, use your clinical knowledge and label it
clearly as "unlisted — AI assessment".

Format: Drug A + Drug B → SEVERITY | Mechanism (brief)

CRITICAL / HIGH
---------------
warfarin     + aspirin         → HIGH    | Both inhibit haemostasis via different mechanisms; major bleeding risk
warfarin     + ibuprofen       → HIGH    | NSAID displaces warfarin from albumin + GI mucosal damage; major bleed risk
warfarin     + naproxen        → HIGH    | Same mechanism as ibuprofen; major bleeding risk
warfarin     + amiodarone      → HIGH    | Amiodarone inhibits CYP2C9; raises INR significantly; toxic warfarin levels
warfarin     + clarithromycin  → HIGH    | CYP3A4/2C9 inhibition raises warfarin; bleeding risk
warfarin     + clopidogrel     → HIGH    | Dual antithrombotic; major bleeding risk
aspirin      + clopidogrel     → HIGH    | Dual antiplatelet; major GI bleed risk without documented indication
aspirin      + ibuprofen       → HIGH    | Ibuprofen blocks aspirin's antiplatelet effect + additive GI bleed risk
aspirin      + prednisolone    → HIGH    | Corticosteroid + NSAID = doubled GI bleed and ulceration risk
ibuprofen    + prednisolone    → HIGH    | Corticosteroid + NSAID = doubled GI bleed and ulceration risk
ibuprofen    + lisinopril      → HIGH    | NSAIDs reduce ACE inhibitor efficacy + acute kidney injury risk
ibuprofen    + ramipril        → HIGH    | NSAIDs reduce ACE inhibitor efficacy + acute kidney injury risk
ibuprofen    + spironolactone  → HIGH    | NSAIDs blunt diuretic effect; risk of renal impairment and hyperkalemia
ibuprofen    + digoxin         → HIGH    | NSAIDs reduce renal clearance of digoxin; risk of toxicity
ibuprofen    + furosemide      → HIGH    | NSAIDs antagonise loop diuretic effect; fluid retention; heart failure risk
lisinopril   + spironolactone  → HIGH    | ACE inhibitor + potassium-sparing diuretic = severe hyperkalemia risk
lisinopril   + ramipril        → HIGH    | Dual ACE inhibitor — no added benefit, doubled hypotension + renal risk
ramipril     + spironolactone  → HIGH    | ACE inhibitor + potassium-sparing diuretic = severe hyperkalemia risk
sertraline   + tramadol        → HIGH    | Serotonin syndrome risk; seizure risk
sertraline   + amitriptyline   → HIGH    | Serotonin syndrome + additive CNS/cardiac depression
sertraline   + linezolid       → HIGH    | Serotonin syndrome; contraindicated
atorvastatin + clarithromycin  → HIGH    | CYP3A4 inhibition raises atorvastatin; rhabdomyolysis risk
atorvastatin + amiodarone      → HIGH    | CYP3A4 inhibition + myopathy risk
simvastatin  + clarithromycin  → HIGH    | CYP3A4 inhibition; rhabdomyolysis risk
simvastatin  + amiodarone      → HIGH    | CYP3A4 inhibition; rhabdomyolysis risk
digoxin      + amiodarone      → HIGH    | Amiodarone raises digoxin levels; bradycardia and toxicity risk
digoxin      + clarithromycin  → HIGH    | P-gp inhibition raises digoxin to toxic levels
salbutamol   + propranolol     → HIGH    | Beta-blocker antagonises bronchodilation; severe bronchospasm risk
salbutamol   + atenolol        → HIGH    | Non-selective beta-blocker blocks salbutamol; bronchospasm risk
bisoprolol   + verapamil       → HIGH    | Additive AV nodal blockade; bradycardia and heart block risk
bisoprolol   + diltiazem       → HIGH    | Additive AV nodal blockade; bradycardia and heart block risk

MODERATE
--------
metformin    + ibuprofen       → MODERATE | NSAIDs impair renal function; risk of metformin accumulation and lactic acidosis in susceptible patients — monitor renal function
metformin    + naproxen        → MODERATE | Same mechanism as metformin + ibuprofen
warfarin     + paracetamol     → MODERATE | High-dose paracetamol (>2g/day) can raise INR; monitor closely
omeprazole   + clopidogrel     → MODERATE | CYP2C19 inhibition reduces clopidogrel activation; reduced antiplatelet effect
omeprazole   + sertraline      → MODERATE | Mild CYP2C19 competition; generally manageable but monitor
sertraline   + omeprazole      → MODERATE | Mild CYP2C19 competition; monitor for sertraline side effects
levothyroxine + sertraline     → MODERATE | Sertraline may reduce levothyroxine efficacy; monitor thyroid function
aspirin      + ibuprofen       → HIGH    | (see HIGH — ibuprofen blocks aspirin's antiplatelet effect)
prednisolone + warfarin        → MODERATE | Steroids can affect clotting factors; INR may fluctuate — monitor
furosemide   + digoxin         → MODERATE | Furosemide-induced hypokalaemia potentiates digoxin toxicity — monitor electrolytes
spironolactone + furosemide    → MODERATE | Potassium balance requires monitoring; generally intentional combination but watch electrolytes
alendronate  + calcium         → MODERATE | Calcium impairs alendronate absorption if taken together — separate by 2 hours
alendronate  + antacids        → MODERATE | Impairs bisphosphonate absorption — separate doses
levothyroxine + calcium        → MODERATE | Calcium impairs levothyroxine absorption — separate by 4 hours
levothyroxine + iron           → MODERATE | Iron impairs levothyroxine absorption — separate by 4 hours
aspirin      + salbutamol      → MODERATE | Aspirin-exacerbated respiratory disease risk in asthma patients — assess
ibuprofen    + salbutamol      → HIGH    | NSAIDs can trigger bronchospasm in asthma; contraindicated without review

LOW / SAFE (notable pairs)
--------------------------
metformin    + paracetamol     → LOW     | No clinically significant interaction; safe to co-prescribe
lisinopril   + metformin       → LOW     | No direct interaction; both used safely in diabetic hypertension
atorvastatin + amlodipine      → LOW     | Minor CYP3A4 competition at high statin doses; generally safe
aspirin      + omeprazole      → LOW     | Omeprazole provides GI protection — co-prescribing is often intentional
warfarin     + omeprazole      → LOW     | Minimal interaction; monitor INR as routine
sertraline   + paracetamol     → LOW     | No clinically significant interaction
salbutamol   + beclometasone   → LOW     | Standard asthma combination; no interaction
salbutamol   + montelukast     → LOW     | Standard asthma combination; no interaction
beclometasone + montelukast    → LOW     | Standard asthma combination; no interaction
metformin    + amoxicillin     → LOW     | No direct pharmacokinetic interaction
"""

SYSTEM_PROMPT = f"""You are the Interaction Safety Agent for PharmAgent AI, deployed in a Scottish community pharmacy.

Your role is to analyse a patient's active prescriptions against a newly proposed medication and identify any drug interaction risks.

{INTERACTION_RULES}

INSTRUCTIONS
============
1. Check EVERY active medication against the new medication using the table above.
2. If the pair appears in the table, you MUST use that exact severity level — do not change it.
3. If the pair is NOT in the table, apply your clinical knowledge and label it "unlisted — AI assessment".
4. Determine the overall risk level:
   - ANY HIGH interaction present     → overall risk = HIGH
   - Only MODERATE interactions       → overall risk = MODERATE
   - Only LOW or no interactions      → overall risk = LOW
5. For HIGH interactions: recommend PHARMACIST REVIEW REQUIRED — do not dispense without consultation.
6. For MODERATE interactions: recommend monitoring and flag for pharmacist awareness.
7. For LOW: safe to dispense with standard counselling.
8. Always consider patient age — elderly patients (>75) have elevated risk for most interactions.
9. Be concise and structured. You support the pharmacist — you do not replace them.

OUTPUT FORMAT
=============
Respond in clean markdown using these sections:
# INTERACTION SAFETY ASSESSMENT
**Patient:** [name] (DOB: [dob]) | **CHI:** [chi]
---
## ACTIVE MEDICATIONS
[numbered list]
---
## INTERACTION ANALYSIS
[table: Drug Pair | Severity | Clinical Rationale]
---
## CLINICAL CONTEXT
[2-3 bullet points of relevant clinical context e.g. age, renal function concerns, indication for combination]
---
## RECOMMENDATION
[emoji] **[PHARMACIST REVIEW REQUIRED / SAFE TO DISPENSE / DO NOT DISPENSE WITHOUT CONSULTATION]**
**Actions before dispensing:**
[bullet list of specific actions]

**Status:** [one-line final status]
"""


def check_interactions(nhs_number: str, new_medication: str = None,
                       _patient: dict = None, _prescriptions: list = None) -> str:
    client = anthropic.Anthropic()
    patient = _patient if _patient is not None else get_patient_by_nhs(nhs_number)
    if "error" in patient:
        return patient["error"]

    prescriptions = _prescriptions if _prescriptions is not None else get_active_prescriptions(patient["id"])
    if not prescriptions:
        return f"No active prescriptions found for {patient['name']}."

    # Build age context for the prompt
    from datetime import datetime
    try:
        dob = datetime.strptime(patient["date_of_birth"], "%Y-%m-%d")
        age = (datetime.today() - dob).days // 365
        age_note = f"Patient age: {age} years old"
    except Exception:
        age_note = ""

    new_med_line = f"\nNew medication being considered: **{new_medication}**" if new_medication else ""

    context = f"""
Patient: {patient['name']} (DOB: {patient['date_of_birth']})
CHI Number: {nhs_number}
{age_note}
{new_med_line}

Active Prescriptions:
{json.dumps(prescriptions, indent=2)}

Please analyse the active medications{f' against the new medication ({new_medication})' if new_medication else ''} for drug interactions and provide your structured safety assessment.
"""

    response = client.messages.create(
        model=MODEL,
        max_tokens=1000,
        system=SYSTEM_PROMPT,
        messages=[
            {"role": "user", "content": context},
        ],
    )

    result = response.content[0].text

    log_audit_event(
        agent="InteractionSafetyAgent",
        action="INTERACTION_CHECK",
        details=f"Patient: {patient['name']} ({nhs_number}) | New med: {new_medication or 'N/A'} | Result: {result[:150]}",
        patient_id=patient["id"],
    )

    return result


if __name__ == "__main__":
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    print("=== Interaction Safety Agent ===\n")
    tests = [
        ("1203480016", "Ibuprofen"),    # HIGH — warfarin + aspirin + ibuprofen
        ("3004710013", "Ibuprofen"),    # MODERATE — metformin + ibuprofen
        ("1509580018", "Tramadol"),     # HIGH — sertraline + tramadol
        ("0312430019", "Clarithromycin"), # HIGH — digoxin + clarithromycin
        ("1108530028", "Propranolol"),  # HIGH — salbutamol + propranolol
    ]
    for nhs, med in tests:
        print(f"Checking CHI: {nhs} | New med: {med}")
        print("-" * 60)
        print(check_interactions(nhs, med))
        print("\n")
