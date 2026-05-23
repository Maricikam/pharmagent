"""
Patient Engagement Agent — PharmAgent AI
==========================================
Generates and sends personalised medication refill reminders to patients
whose prescriptions are due within a configurable time window.

Responsibility:
    Identifies patients with upcoming prescription due dates, generates
    a personalised message for each patient based on their medication
    history and name, and dispatches via SMS or email.

    Patients are scored for adherence risk using population-level statistics
    derived from the patient adherence dataset (5,000 records). High-risk
    patients are prioritised in the outreach queue and receive more
    personalised, supportive messaging.

Tools used:
    - get_patients_due_for_refill() — filter patients by due date window
    - get_active_prescriptions()    — fetch current medication list for risk scoring
    - send_patient_message()        — dispatch SMS/email via Twilio/NHS Notify
    - log_audit_entry()             — write action to audit trail

Output:
    Campaign summary including patients contacted, message previews,
    delivery status, adherence risk scores, and sort order (high risk first).
"""

import csv
import os
import anthropic
import json
from datetime import datetime
from tools.pharmacy_tools import (get_patients_due_refill, get_active_prescriptions,
                                   send_patient_message, log_audit_event)
from config import MODEL


# ---------------------------------------------------------------------------
# ADHERENCE RISK LOADER
# Derives non-adherence rates by age band and comorbidity count from the
# patient_adherence_dataset.csv (5,000 records). Used to score each patient
# in the engagement campaign and prioritise outreach.
# Falls back to hardcoded rates if the file is absent (Railway deployment).
# ---------------------------------------------------------------------------

_FALLBACK_AGE_RATES = {
    "18-44": 0.524,
    "45-59": 0.546,
    "60-74": 0.555,
    "75+":   0.606,
}

_FALLBACK_COMORBID_RATES = {0: 0.527, 1: 0.530, 2: 0.565, 3: 0.539,
                             4: 0.554, 5: 0.506, 6: 0.588}

_AGE_RATES: dict[str, float] = {}
_COMORBID_RATES: dict[int, float] = {}


def _load_adherence_stats() -> tuple[dict, dict]:
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    csv_path = os.path.join(base, "data", "patient_adherence_dataset.csv")

    try:
        with open(csv_path, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
    except FileNotFoundError:
        return _FALLBACK_AGE_RATES, _FALLBACK_COMORBID_RATES

    # Age-band non-adherence rates
    age_buckets: dict[str, list] = {"18-44": [], "45-59": [], "60-74": [], "75+": []}
    comorbid_buckets: dict[int, list] = {}

    for r in rows:
        age = int(r["Age"])
        val = int(r["Adherence"])
        cc = int(r["Comorbidities_Count"])

        if age < 45:
            age_buckets["18-44"].append(val)
        elif age < 60:
            age_buckets["45-59"].append(val)
        elif age < 75:
            age_buckets["60-74"].append(val)
        else:
            age_buckets["75+"].append(val)

        comorbid_buckets.setdefault(cc, []).append(val)

    age_rates = {band: 1 - sum(v) / len(v) for band, v in age_buckets.items() if v}
    comorbid_rates = {k: 1 - sum(v) / len(v) for k, v in comorbid_buckets.items()}

    return age_rates, comorbid_rates


_AGE_RATES, _COMORBID_RATES = _load_adherence_stats()


# Mental-health proxy: medications that suggest a mental health condition,
# which the dataset shows increases non-adherence risk by ~11 percentage points.
_MENTAL_HEALTH_MEDS = {"sertraline", "amitriptyline", "citalopram", "fluoxetine",
                        "venlafaxine", "paroxetine", "mirtazapine", "quetiapine",
                        "olanzapine", "lithium", "diazepam", "zopiclone"}


def _age_band(age: int) -> str:
    if age < 45:
        return "18-44"
    elif age < 60:
        return "45-59"
    elif age < 75:
        return "60-74"
    return "75+"


def adherence_risk_score(age: int, num_prescriptions: int,
                          generic_names: list[str] | None = None) -> dict:
    """
    Score a patient's non-adherence risk based on population statistics.

    Returns:
        risk_level: HIGH / MEDIUM / LOW
        risk_score: float 0-1 (estimated non-adherence probability)
        factors:    list of contributing risk factors
    """
    band = _age_band(age)
    age_rate = _AGE_RATES.get(band, 0.545)

    # Cap comorbidity lookup at max observed key
    cc = min(num_prescriptions, max(_COMORBID_RATES.keys(), default=0))
    comorbid_rate = _COMORBID_RATES.get(cc, 0.545)

    # Weighted average: age 40%, comorbidities 40%, baseline 20%
    score = 0.4 * age_rate + 0.4 * comorbid_rate + 0.2 * 0.545

    factors = []
    if age >= 75:
        factors.append(f"age {age} (75+ band: {_AGE_RATES.get('75+', 0.606)*100:.0f}% non-adherence rate)")
    elif age >= 60:
        factors.append(f"age {age} (60-74 band: {_AGE_RATES.get('60-74', 0.555)*100:.0f}% non-adherence rate)")

    if num_prescriptions >= 3:
        factors.append(f"{num_prescriptions} active prescriptions (complex regimen)")

    # Mental health medication proxy (+11 pp uplift from dataset)
    if generic_names:
        mh_meds = [g for g in generic_names if g.lower() in _MENTAL_HEALTH_MEDS]
        if mh_meds:
            score = min(score + 0.11, 1.0)
            factors.append(f"mental health medication ({', '.join(mh_meds)})")

    if score >= 0.57:
        risk_level = "HIGH"
    elif score >= 0.545:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"

    if not factors:
        factors.append("within average non-adherence range")

    return {
        "risk_level": risk_level,
        "risk_score": round(score, 3),
        "factors": factors,
    }


# ---------------------------------------------------------------------------
# SYSTEM PROMPT
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are the Patient Engagement Agent for PharmAgent AI, a community pharmacy in Scotland.

Your role is to write personalised, warm, professional refill reminder messages for patients.

Guidelines:
- Address the patient by first name
- Mention the specific medication(s) due
- Keep SMS messages under 160 characters
- Keep email messages friendly, brief (3-4 sentences max), and professional
- Include a call to action: phone the pharmacy or visit in person
- Never share clinical details that could embarrass the patient
- The pharmacy phone number is 0141 555 0199
- The pharmacy name is Renfrew Road Pharmacy

Adherence risk guidance:
- HIGH RISK patients: write a warmer, more personal message — acknowledge that keeping on top of medications can be difficult and offer support. Slightly more urgent tone.
- MEDIUM RISK patients: standard professional reminder with a friendly check-in element.
- LOW RISK patients: brief, efficient reminder — they are reliable, so keep it short.

Write in plain, accessible English. Many patients are elderly — avoid jargon."""


def generate_refill_message(patient_name: str, first_name: str, medications: list[str],
                             next_due: str, channel: str, campaign_type: str = "refill_reminder",
                             risk_level: str = "MEDIUM") -> str:
    """Ask Claude to generate a personalised message for one patient."""
    client = anthropic.Anthropic()
    med_list = ", ".join(medications)

    type_instructions = {
        "refill_reminder": "Write a refill reminder — their prescription is due soon.",
        "adherence_check": "Write a gentle, caring check-in — we haven't seen them collect their medication recently. Are they okay? Encourage them to call.",
        "seasonal": "Write a seasonal health check invitation — invite them in for a free health check this season.",
        "flu_vaccination": (
            "Write a flu vaccination invitation. Mention that the pharmacy is now offering free NHS flu jabs "
            "for eligible patients. Note that their medications may put them in an at-risk group. "
            "Encourage them to pop in or call to book — no appointment usually needed."
        ),
        "spring_allergies": (
            "Write a spring hay fever and allergy season message. Mention that pollen counts are rising and "
            "the pharmacy has antihistamines and nasal sprays in stock. If their current medications include "
            "anything that interacts with antihistamines, remind them to ask the pharmacist before buying "
            "over-the-counter remedies. Friendly and helpful tone."
        ),
        "winter_wellness": (
            "Write a winter wellness message. Remind the patient to keep warm, stay on top of their regular "
            "medications during the cold months, and consider vitamin D supplements as daylight shortens. "
            "Mention the pharmacy can help with cold and flu remedies and is happy to do a free medicines review."
        ),
        "travel_health": (
            "Write a pre-travel health reminder. The patient may be travelling soon. Remind them to collect "
            "enough of their regular medications to cover the trip (plus spare), and to ask the pharmacist "
            "about any travel vaccinations, antimalarials, or interactions with sun/heat. Warm, practical tone."
        ),
        "new_year_health": (
            "Write a New Year health goals message. It's a new year — a good time for a free NHS medicines "
            "review at the pharmacy. Mention that a pharmacist can check all their medications are still "
            "right for them, discuss any side effects they've been putting up with, and help with any "
            "health goals like stopping smoking or losing weight."
        ),
        "photosensitivity_summer": (
            "Write a summer sun safety message. Some of their medications increase sensitivity to sunlight — "
            "remind them to use SPF 30+ sunscreen, wear a hat in strong sun, and avoid peak UV hours. "
            "Keep it brief and practical. Mention the pharmacy stocks a range of high-factor sunscreens."
        ),
    }
    instruction = type_instructions.get(campaign_type, type_instructions["refill_reminder"])

    prompt = f"""
Patient: {patient_name} (first name: {first_name})
Medications: {med_list}
Due date: {next_due}
Channel: {channel} ({'max 160 characters' if channel == 'sms' else 'short friendly email'})
Adherence risk: {risk_level}

{instruction}
Return ONLY the message text itself — no preamble, no markdown, no character count, no "Here's an SMS..." introduction. Just the message the patient would receive.
"""
    response = client.messages.create(
        model=MODEL,
        max_tokens=300,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text.strip()


def run_engagement_campaign(days_ahead: int = 7, channel: str = "sms",
                             campaign_type: str = "refill_reminder") -> dict:
    """
    Find all patients due for refills in the next N days and send them a reminder.
    Patients are scored for adherence risk and sorted highest-risk first.
    Returns a summary of all outreach actions taken.
    """
    patients_due = get_patients_due_refill(days_ahead=days_ahead)

    if not patients_due:
        return {"message": "No patients due for refills in this window.",
                "sent": [], "patients_contacted": 0, "results": []}

    # Group by patient and collect due medications
    patient_map: dict[int, dict] = {}
    for p in patients_due:
        pid = p["patient_id"]
        if pid not in patient_map:
            patient_map[pid] = {
                "patient_id": pid,
                "name": p["name"],
                "first_name": p["name"].split()[0],
                "phone": p["phone"],
                "email": p["email"],
                "next_due_date": p["next_due_date"],
                "medications": [],
            }
        patient_map[pid]["medications"].append(p["medication"])

    # Score adherence risk for each patient
    for pid, data in patient_map.items():
        prescriptions = get_active_prescriptions(pid)
        generic_names = [rx.get("generic_name", "") for rx in prescriptions]

        dob_str = None
        for rx in prescriptions:
            break

        # Derive age from patient DOB via a quick DB lookup through tools
        age = 60  # safe default if DOB unavailable
        try:
            from tools.pharmacy_tools import _db
            from db.models import Patient
            db = _db()
            patient_row = db.query(Patient).filter(Patient.id == pid).first()
            if patient_row and patient_row.date_of_birth:
                dob = datetime.strptime(patient_row.date_of_birth, "%Y-%m-%d")
                age = (datetime.today() - dob).days // 365
            db.close()
        except Exception:
            pass

        risk = adherence_risk_score(
            age=age,
            num_prescriptions=len(prescriptions),
            generic_names=generic_names,
        )
        data["age"] = age
        data["adherence_risk"] = risk

    # Sort: HIGH risk first, then MEDIUM, then LOW
    _order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    sorted_patients = sorted(
        patient_map.values(),
        key=lambda p: (_order.get(p["adherence_risk"]["risk_level"], 1),
                       -p["adherence_risk"]["risk_score"]),
    )

    results = []
    for data in sorted_patients:
        risk = data["adherence_risk"]
        message = generate_refill_message(
            patient_name=data["name"],
            first_name=data["first_name"],
            medications=data["medications"],
            next_due=data["next_due_date"],
            channel=channel,
            campaign_type=campaign_type,
            risk_level=risk["risk_level"],
        )
        send_result = send_patient_message(
            patient_id=data["patient_id"],
            channel=channel,
            message=message,
        )
        try:
            due = datetime.strptime(data["next_due_date"], "%Y-%m-%d")
            days_until_due = (due - datetime.today().replace(
                hour=0, minute=0, second=0, microsecond=0)).days
        except Exception:
            days_until_due = None

        results.append({
            "patient": data["name"],
            "age": data["age"],
            "channel": channel,
            "message": message,
            "send_status": send_result.get("status"),
            "days_until_due": days_until_due,
            "medications": data["medications"],
            "adherence_risk": risk["risk_level"],
            "risk_score": risk["risk_score"],
            "risk_factors": risk["factors"],
        })

    log_audit_event(
        agent="PatientEngagementAgent",
        action="ENGAGEMENT_CAMPAIGN",
        details=(
            f"Campaign: {len(results)} messages sent via {channel} | "
            f"Window: {days_ahead} days | "
            f"High-risk: {sum(1 for r in results if r['adherence_risk'] == 'HIGH')}"
        ),
    )

    return {
        "patients_contacted": len(results),
        "channel": channel,
        "results": results,
    }


if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    print("=== Patient Engagement Agent ===")
    print(f"Adherence stats loaded from: {'CSV dataset' if _AGE_RATES != _FALLBACK_AGE_RATES else 'fallback'}")
    print(f"75+ non-adherence rate: {_AGE_RATES.get('75+', 0)*100:.1f}%\n")
    print("Finding patients due for refills in the next 7 days...\n")
    result = run_engagement_campaign(days_ahead=7, channel="sms")
    print(f"Contacted {result['patients_contacted']} patients\n")
    for r in result["results"]:
        print(f"  {r['patient']} | Age {r['age']} | Risk: {r['adherence_risk']} ({r['risk_score']:.3f})")
        print(f"  Factors: {'; '.join(r['risk_factors'])}")
        print(f"  Message: {r['message'][:120]}...")
        print()
