"""
Analytics Agent — PharmAgent AI
=================================
Provides predictive insights: patient prioritization, anomaly detection,
and automatic workflow optimization recommendations.

Responsibility:
    - prioritize_patients: scores every patient by clinical urgency
      (overdue collection, adherence risk, polypharmacy) and returns a
      sorted action list for the pharmacist.
    - detect_anomalies: identifies unusual patterns across stock demand,
      patient collections, and audit activity.
    - get_workflow_optimization: generates AI-driven workflow improvement
      suggestions based on current pharmacy state and audit history.

Design note:
    Reads from the same tool layer as all other agents. Does not write
    to the database — all outputs are advisory.
"""

import anthropic
import json
from datetime import datetime
from tools.pharmacy_tools import (
    get_anomaly_signals, get_prescription_demand, get_overdue_patients,
    get_recent_audit_logs, log_audit_event,
)
from config import MODEL

SYSTEM_PROMPT = """You are the Analytics Agent for PharmAgent AI.
Your role is to detect patterns, prioritise patients, and optimise pharmacy workflow.

Output format:
- Professional NHS clinical tone
- No emojis or decorative symbols
- NEVER use markdown: no #/##/### headers, no | tables |, no ** bold **, no * bullets *
- Write section headers as plain text on their own line followed by a line of dashes, e.g.:
  URGENT PATIENTS
  ---------------
- DD/MM/YYYY dates, 24-hour time
- Use [URGENT], [HIGH], [ROUTINE] for patient priority
- Use [CRITICAL], [WARNING], [ADVISORY] for anomaly severity
- End with numbered priority actions"""


def prioritize_patients() -> dict:
    """Score and rank all patients by clinical urgency."""
    from db.database import SessionLocal
    from db.models import Patient, Prescription
    from agents.patient_engagement_agent import adherence_risk_score

    db = SessionLocal()
    try:
        today = datetime.today()
        patients = db.query(Patient).all()
        scored = []
        for p in patients:
            rxs = (db.query(Prescription)
                   .filter(Prescription.patient_id == p.id, Prescription.active == True)
                   .all())
            if not rxs:
                continue

            overdue_days = 0
            for rx in rxs:
                if rx.next_due_date:
                    try:
                        due = datetime.strptime(rx.next_due_date, "%Y-%m-%d")
                        if due < today:
                            overdue_days = max(overdue_days, (today - due).days)
                    except Exception:
                        pass

            num_meds = len(rxs)
            age = None
            if p.date_of_birth:
                try:
                    dob = datetime.strptime(p.date_of_birth, "%Y-%m-%d")
                    age = (today - dob).days // 365
                except Exception:
                    pass

            generics = [rx.medication.generic_name for rx in rxs if rx.medication.generic_name]
            risk_result = (
                adherence_risk_score(age, num_meds, generics)
                if age else {"risk_level": "LOW", "risk_score": 0.5}
            )

            score = overdue_days * 3 + risk_result.get("risk_score", 0.5) * 20 + num_meds

            if overdue_days > 0:
                priority = "URGENT"
            elif risk_result["risk_level"] == "HIGH":
                priority = "HIGH"
            else:
                priority = "ROUTINE"

            scored.append({
                "patient_id": p.id,
                "name": f"{p.first_name} {p.last_name}",
                "nhs_number": p.nhs_number,
                "priority": priority,
                "urgency_score": round(score, 1),
                "overdue_days": overdue_days,
                "num_medications": num_meds,
                "medications": [rx.medication.name for rx in rxs],
                "adherence_risk": risk_result["risk_level"],
                "risk_factors": risk_result.get("factors", []),
            })
    finally:
        db.close()

    scored.sort(key=lambda x: x["urgency_score"], reverse=True)

    client = anthropic.Anthropic()
    context = f"""
Patient Priority List
---------------------
Date: {datetime.today().strftime('%d/%m/%Y')}

{json.dumps(scored, indent=2)}

Provide a structured patient prioritization report.
Group patients by URGENT -> HIGH -> ROUTINE.
For each URGENT patient, state clearly what action is needed today.
"""
    response = client.messages.create(
        model=MODEL,
        max_tokens=900,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": context}],
    )

    log_audit_event(
        agent="AnalyticsAgent",
        action="PATIENT_PRIORITIZATION",
        details=f"Scored {len(scored)} patients | Urgent: {sum(1 for p in scored if p['priority'] == 'URGENT')} | High: {sum(1 for p in scored if p['priority'] == 'HIGH')}",
    )

    return {
        "patients": scored,
        "report": response.content[0].text,
        "urgent_count": sum(1 for p in scored if p["priority"] == "URGENT"),
        "high_count": sum(1 for p in scored if p["priority"] == "HIGH"),
        "routine_count": sum(1 for p in scored if p["priority"] == "ROUTINE"),
    }


def detect_anomalies() -> dict:
    """Detect unusual patterns across stock, prescriptions, and patient behaviour."""
    signals = get_anomaly_signals()
    demand = get_prescription_demand()

    client = anthropic.Anthropic()
    context = f"""
Anomaly Detection Report
------------------------
Date: {datetime.today().strftime('%d/%m/%Y')}

OVERDUE PATIENT COLLECTIONS:
Count: {signals['overdue_patients']}
Details: {json.dumps(signals['overdue_details'], indent=2)}

POLYPHARMACY PATIENTS (5 or more active medications):
Count: {signals['polypharmacy_patients']}
Details: {json.dumps(signals['polypharmacy_details'], indent=2)}

EMERGENCY SUPPLIES IN LAST 7 DAYS: {signals['recent_emergency_supplies']}

STOCK SHORTAGE RISK (fewer than 14 days supply at current prescription demand):
{json.dumps(signals['shortage_risk_items'], indent=2)}

PRESCRIPTION DEMAND (top 10 by demand):
{json.dumps(demand[:10], indent=2)}

Analyse these signals for anomalies. Assign [CRITICAL], [WARNING], or [ADVISORY] severity.
For each anomaly: state what it is, why it is concerning, and what action to take.
"""
    response = client.messages.create(
        model=MODEL,
        max_tokens=900,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": context}],
    )

    log_audit_event(
        agent="AnalyticsAgent",
        action="ANOMALY_DETECTION",
        details=(
            f"Overdue={signals['overdue_patients']} | "
            f"Polypharmacy={signals['polypharmacy_patients']} | "
            f"Emergency7d={signals['recent_emergency_supplies']} | "
            f"ShortageRisk={len(signals['shortage_risk_items'])}"
        ),
    )

    return {
        "signals": signals,
        "report": response.content[0].text,
        "anomaly_count": (
            signals["overdue_patients"]
            + signals["polypharmacy_patients"]
            + signals["recent_emergency_supplies"]
            + len(signals["shortage_risk_items"])
        ),
    }


def get_workflow_optimization() -> dict:
    """AI workflow optimization recommendations based on pharmacy state and audit history."""
    signals = get_anomaly_signals()
    demand = get_prescription_demand()
    recent_logs = get_recent_audit_logs(limit=50)

    action_counts: dict = {}
    for log in recent_logs:
        action_counts[log["action"]] = action_counts.get(log["action"], 0) + 1

    client = anthropic.Anthropic()
    context = f"""
Workflow Optimization Analysis
-------------------------------
Date: {datetime.today().strftime('%d/%m/%Y')}

RECENT AUDIT ACTIVITY (last 50 events by type):
{json.dumps(action_counts, indent=2)}

PATIENT LOAD INDICATORS:
- Overdue collections: {signals['overdue_patients']}
- Polypharmacy patients: {signals['polypharmacy_patients']}
- Emergency supplies (last 7 days): {signals['recent_emergency_supplies']}

MEDICATION DEMAND (top 10 by prescription count):
{json.dumps(demand[:10], indent=2)}

Based on this data, provide specific workflow optimization recommendations.
Focus on: reorder threshold adjustments, patient outreach scheduling, workload distribution,
and process improvements that would reduce emergency supplies and overdue collections.
Use [IMMEDIATE], [THIS WEEK], [NEXT MONTH] timeframes for each recommendation.
"""
    response = client.messages.create(
        model=MODEL,
        max_tokens=900,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": context}],
    )

    log_audit_event(
        agent="AnalyticsAgent",
        action="WORKFLOW_OPTIMIZATION",
        details=f"Analyzed {len(recent_logs)} audit events | Demand data for {len(demand)} medications",
    )

    return {
        "report": response.content[0].text,
        "demand_data": demand,
        "action_counts": action_counts,
    }
