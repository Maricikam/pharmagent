"""
Patient Engagement Agent — PharmAgent AI
==========================================
Generates and sends personalised medication refill reminders to patients
whose prescriptions are due within a configurable time window.

Responsibility:
    Identifies patients with upcoming prescription due dates, generates
    a personalised message for each patient based on their medication
    history and name, and dispatches via SMS or email.

Tools used:
    - get_patients_due_for_refill() — filter patients by due date window
    - send_patient_message()        — dispatch SMS/email via Twilio/NHS Notify
    - log_audit_entry()             — write action to audit trail

Output:
    Campaign summary including patients contacted, message previews,
    delivery status, and patients skipped (opted out or recently contacted).

Note:
    In demo/development mode, messages are simulated and logged rather
    than dispatched. Production deployment uses Twilio API or NHS Notify
    for real SMS delivery.
"""

"""
Patient Engagement Agent
Identifies patients due for refills and generates personalised,
compassionate outreach messages. Simulates sending via SMS or email.
"""
import anthropic
import json
from datetime import datetime
from tools.pharmacy_tools import (get_patients_due_refill, get_active_prescriptions,
                                   send_patient_message, log_audit_event)
from config import MODEL

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

Write in plain, accessible English. Many patients are elderly — avoid jargon."""


def generate_refill_message(patient_name: str, first_name: str, medications: list[str],
                             next_due: str, channel: str, campaign_type: str = "refill_reminder") -> str:
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

def run_engagement_campaign(days_ahead: int = 7, channel: str = "sms", campaign_type: str = "refill_reminder") -> dict:
    """
    Find all patients due for refills in the next N days and send them a reminder.
    Returns a summary of all outreach actions taken.
    """
    patients_due = get_patients_due_refill(days_ahead=days_ahead)

    if not patients_due:
        return {"message": "No patients due for refills in this window.", "sent": [], "patients_contacted": 0, "results": []}

    results = []
    # Group by patient to collect all their due medications
    patient_map = {}
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

    for pid, data in patient_map.items():
        message = generate_refill_message(
            patient_name=data["name"],
            first_name=data["first_name"],
            medications=data["medications"],
            next_due=data["next_due_date"],
            channel=channel,
            campaign_type=campaign_type,
        )
        send_result = send_patient_message(
            patient_id=pid,
            channel=channel,
            message=message,
        )
        try:
            due = datetime.strptime(data["next_due_date"], "%Y-%m-%d")
            days_until_due = (due - datetime.today().replace(hour=0, minute=0, second=0, microsecond=0)).days
        except Exception:
            days_until_due = None
        results.append({
            "patient": data["name"],
            "channel": channel,
            "message": message,
            "send_status": send_result.get("status"),
            "days_until_due": days_until_due,
            "medications": data["medications"],
        })

    log_audit_event(
        agent="PatientEngagementAgent",
        action="ENGAGEMENT_CAMPAIGN",
        details=f"Refill campaign: {len(results)} messages sent via {channel} | Window: {days_ahead} days",
    )

    return {
        "patients_contacted": len(results),
        "channel": channel,
        "results": results,
    }


if __name__ == "__main__":
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    print("=== Patient Engagement Agent ===\n")
    print("Finding patients due for refills in the next 7 days...\n")
    result = run_engagement_campaign(days_ahead=7, channel="sms")
    print(f"Contacted {result['patients_contacted']} patients\n")
    for r in result["results"]:
        print(f"  👤 {r['patient']} ({r['channel'].upper()}) — Status: {r['send_status']}")
        print(f"     Message: {r['message'][:120]}...")
        print()