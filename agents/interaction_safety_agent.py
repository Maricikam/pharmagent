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

import re
import json
import os
import anthropic
from tools.pharmacy_tools import get_patient_by_nhs, get_active_prescriptions, log_audit_event
from config import MODEL


def _strip_md(text: str) -> str:
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'\*(.+?)\*', r'\1', text)
    text = re.sub(r'^#{1,3}\s*', '', text, flags=re.MULTILINE)
    text = re.sub(r'^-{3,}$', '', text, flags=re.MULTILINE)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


# ---------------------------------------------------------------------------
# DDI DATABASE LOADER
# Loads from data/Interaction Safety Agent.json (80 validated clinical records
# sourced from DrugBank 6.0, Micromedex, FDA, and peer-reviewed literature).
# Falls back to hardcoded rules if the file is not present (e.g. local dev
# without the data folder).
# ---------------------------------------------------------------------------

_SEVERITY_MAP = {"major": "HIGH", "moderate": "MODERATE", "minor": "LOW"}

_HARDCODED_RULES = """
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
warfarin     + amiodarone      → HIGH    | Amiodarone inhibits CYP2C9; raises INR significantly; toxic warfarin levels
warfarin     + clarithromycin  → HIGH    | CYP3A4/2C9 inhibition raises warfarin; bleeding risk
aspirin      + ibuprofen       → HIGH    | Ibuprofen blocks aspirin antiplatelet effect + additive GI bleed risk
ibuprofen    + lisinopril      → HIGH    | NSAIDs reduce ACE inhibitor efficacy + acute kidney injury risk
ibuprofen    + ramipril        → HIGH    | NSAIDs reduce ACE inhibitor efficacy + acute kidney injury risk
sertraline   + tramadol        → HIGH    | Serotonin syndrome risk; seizure risk
atorvastatin + clarithromycin  → HIGH    | CYP3A4 inhibition raises atorvastatin; rhabdomyolysis risk
digoxin      + amiodarone      → HIGH    | Amiodarone raises digoxin levels; bradycardia and toxicity risk
salbutamol   + propranolol     → HIGH    | Beta-blocker antagonises bronchodilation; severe bronchospasm risk

MODERATE
--------
metformin    + ibuprofen       → MODERATE | NSAIDs impair renal function; risk of metformin accumulation
warfarin     + paracetamol     → MODERATE | High-dose paracetamol can raise INR; monitor closely
omeprazole   + clopidogrel     → MODERATE | CYP2C19 inhibition reduces clopidogrel activation

LOW / SAFE (notable pairs)
--------------------------
metformin    + paracetamol     → LOW     | No clinically significant interaction; safe to co-prescribe
aspirin      + omeprazole      → LOW     | Omeprazole provides GI protection; co-prescribing is often intentional
"""

_DDI_RECORDS: list = []


def _load_ddi_database() -> tuple[str, list]:
    """
    Load DDI rules from JSON dataset.
    Returns (rules_text, records_list).
    """
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    json_path = os.path.join(base_dir, "data", "Interaction Safety Agent.json")

    try:
        with open(json_path, encoding="utf-8") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return _HARDCODED_RULES, []

    records = []
    by_severity: dict[str, list] = {"HIGH": [], "MODERATE": [], "LOW": []}

    for rec in data.get("ddi_database", []):
        sev = _SEVERITY_MAP.get(rec.get("severity", "").lower(), "MODERATE")
        drug_a = rec.get("drug_a", "").strip()
        drug_b = rec.get("drug_b", "").strip()
        mechanism = rec.get("mechanism", "")
        short_mech = mechanism[:110] + "…" if len(mechanism) > 110 else mechanism

        by_severity[sev].append(
            f"{drug_a:<25} + {drug_b:<35} → {sev:<8} | {short_mech}"
        )
        records.append({
            "drug_a": drug_a.lower(),
            "drug_b": drug_b.lower(),
            "severity": sev,
            "mechanism": mechanism,
            "clinical_effect": rec.get("clinical_effect", ""),
            "safer_alternative": rec.get("safer_alternative", ""),
            "clinical_management": rec.get("clinical_management", ""),
        })

    header = (
        "MANDATORY INTERACTION SEVERITY TABLE\n"
        "=====================================\n"
        "Source: DrugBank 6.0, Micromedex, FDA Drug Safety Communications.\n"
        "You MUST use the exact severity level from this table when the drug pair\n"
        "is present. Do not upgrade or downgrade based on your own reasoning.\n"
        "If a pair is not in this table, use your clinical knowledge and label it\n"
        'clearly as "unlisted — AI assessment".\n\n'
        "Format: Drug A + Drug B → SEVERITY | Mechanism (brief)\n"
    )

    sections = ""
    for label, lines in [
        ("CRITICAL / HIGH", by_severity["HIGH"]),
        ("MODERATE", by_severity["MODERATE"]),
        ("LOW / SAFE", by_severity["LOW"]),
    ]:
        if lines:
            sections += f"\n{label}\n{'-' * len(label)}\n"
            sections += "\n".join(lines) + "\n"

    return header + sections, records


INTERACTION_RULES, _DDI_RECORDS = _load_ddi_database()


def _find_relevant_ddi(active_meds: list, new_medication: str | None) -> list:
    """
    Return DDI records where both drugs in the pair are present in the
    combined medication list (active + new). Uses case-insensitive substring
    matching to handle branded names like 'Warfarin 5mg'.
    """
    if not _DDI_RECORDS:
        return []

    med_names = []
    for rx in active_meds:
        name = rx.get("medication", rx.get("medication_name", "")).lower()
        generic = rx.get("generic_name", "").lower()
        if name:
            med_names.append(name)
        if generic and generic != name:
            med_names.append(generic)
    if new_medication:
        med_names.append(new_medication.lower())

    def _matches(ddi_drug: str, meds: list[str]) -> bool:
        for m in meds:
            if ddi_drug in m or m in ddi_drug:
                return True
        return False

    matched = []
    seen: set[tuple] = set()

    for rec in _DDI_RECORDS:
        da, db = rec["drug_a"], rec["drug_b"]
        key = tuple(sorted([da, db]))
        if key in seen:
            continue
        if _matches(da, med_names) and _matches(db, med_names):
            seen.add(key)
            matched.append(rec)

    return matched


# ---------------------------------------------------------------------------
# SYSTEM PROMPT
# ---------------------------------------------------------------------------

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
9. Where a DETAILED INTERACTION RECORD is provided in the user message, use the safer_alternative
   and clinical_management fields to enrich your recommendation — cite them directly.
10. Be concise and structured. You support the pharmacist — you do not replace them.

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
[bullet list — for each interaction: drug pair, severity level, clinical rationale]
---
## CLINICAL CONTEXT
[2-3 bullet points of relevant clinical context e.g. age, renal function concerns, indication for combination]
---
## RECOMMENDATION
**[PHARMACIST REVIEW REQUIRED / SAFE TO DISPENSE / DO NOT DISPENSE WITHOUT CONSULTATION]**
**Actions before dispensing:**
[bullet list of specific actions including safer alternatives where applicable]

**Status:** [one-line final status]
"""


def _severity_to_recommendation(severity: str) -> str:
    if severity == "HIGH":
        return "DO NOT DISPENSE without prescriber review"
    if severity == "MODERATE":
        return "Pharmacist review recommended — monitor closely"
    return "Safe to dispense with standard counselling"


def _overall_risk_level(matched_ddi: list, report_text: str) -> str:
    if any(m["severity"] == "HIGH" for m in matched_ddi):
        return "HIGH"
    if any(m["severity"] == "MODERATE" for m in matched_ddi):
        return "MODERATE"
    if matched_ddi:
        return "LOW"
    t = report_text.upper()
    if "DO NOT DISPENSE" in t or re.search(r"\bHIGH\b", t):
        return "HIGH"
    if "PHARMACIST REVIEW" in t or re.search(r"\bMODERATE\b", t):
        return "MODERATE"
    return "LOW"


def check_interactions(nhs_number: str, new_medication: str = None,
                       _patient: dict = None, _prescriptions: list = None) -> dict:
    """
    Returns a dict with keys:
        text                — full clinical report (markdown)
        risk_level          — HIGH / MODERATE / LOW
        interactions_detected — list of structured interaction records
        patient             — patient dict
        prescriptions       — list of active prescription dicts
    """
    client = anthropic.Anthropic()
    patient = _patient if _patient is not None else get_patient_by_nhs(nhs_number)
    if "error" in patient:
        return {"text": patient["error"], "risk_level": "UNKNOWN",
                "interactions_detected": [], "patient": patient, "prescriptions": []}

    prescriptions = _prescriptions if _prescriptions is not None else get_active_prescriptions(patient["id"])
    if not prescriptions:
        msg = f"No active prescriptions found for {patient['name']}."
        return {"text": msg, "risk_level": "LOW",
                "interactions_detected": [], "patient": patient, "prescriptions": []}

    from datetime import datetime
    try:
        dob = datetime.strptime(patient["date_of_birth"], "%Y-%m-%d")
        age = (datetime.today() - dob).days // 365
        age_note = f"Patient age: {age} years old"
    except Exception:
        age = None
        age_note = ""

    new_med_line = f"\nNew medication being considered: **{new_medication}**" if new_medication else ""

    matched_ddi = _find_relevant_ddi(prescriptions, new_medication)
    ddi_section = ""
    if matched_ddi:
        ddi_section = "\n\nDETAILED INTERACTION RECORDS (from DrugBank/Micromedex database)\n"
        ddi_section += "=" * 65 + "\n"
        for m in matched_ddi:
            ddi_section += (
                f"\nPair: {m['drug_a'].title()} + {m['drug_b'].title()}\n"
                f"Severity: {m['severity']}\n"
                f"Mechanism: {m['mechanism']}\n"
                f"Clinical effect: {m['clinical_effect']}\n"
                f"Safer alternative: {m['safer_alternative']}\n"
                f"Clinical management: {m['clinical_management']}\n"
            )

    context = f"""
Patient: {patient['name']} (DOB: {patient['date_of_birth']})
CHI Number: {nhs_number}
{age_note}
{new_med_line}

Active Prescriptions:
{json.dumps(prescriptions, indent=2)}
{ddi_section}
Please analyse the active medications{f' against the new medication ({new_medication})' if new_medication else ''} for drug interactions and provide your structured safety assessment.
"""

    response = client.messages.create(
        model=MODEL,
        max_tokens=1000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": context}],
    )

    report_text = response.content[0].text
    risk_level = _overall_risk_level(matched_ddi, report_text)

    interactions_detected = [
        {
            "drug_a": m["drug_a"].title(),
            "drug_b": m["drug_b"].title(),
            "severity": m["severity"],
            "mechanism": m["mechanism"],
            "clinical_effect": m["clinical_effect"],
            "safer_alternative": m["safer_alternative"],
            "clinical_management": m["clinical_management"],
            "recommendation": _severity_to_recommendation(m["severity"]),
            "evidence_source": "DrugBank/Micromedex DDI Database",
        }
        for m in matched_ddi
    ]

    log_audit_event(
        agent="InteractionSafetyAgent",
        action="INTERACTION_CHECK",
        details=f"Patient: {patient['name']} ({nhs_number}) | New med: {new_medication or 'N/A'} | Risk: {risk_level} | DDI matches: {len(matched_ddi)}",
        patient_id=patient["id"],
    )

    return {
        "text": report_text,
        "risk_level": risk_level,
        "interactions_detected": interactions_detected,
        "patient": patient,
        "prescriptions": prescriptions,
        "age": age,
    }


if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    print(f"=== Interaction Safety Agent ===")
    print(f"DDI database loaded: {len(_DDI_RECORDS)} records\n")
    tests = [
        ("1203480016", "Ibuprofen"),      # HIGH — warfarin + aspirin + ibuprofen
        ("3004710013", "Ibuprofen"),      # MODERATE — metformin + ibuprofen
        ("1509580018", "Tramadol"),       # HIGH — sertraline + tramadol
        ("0312430019", "Clarithromycin"), # HIGH — digoxin + clarithromycin
        ("1108530028", "Propranolol"),    # HIGH — salbutamol + propranolol
    ]
    for nhs, med in tests:
        print(f"Checking CHI: {nhs} | New med: {med}")
        print("-" * 60)
        print(check_interactions(nhs, med))
        print("\n")
