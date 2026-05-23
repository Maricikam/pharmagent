"""
Handover Agent — PharmAgent AI
================================
Generates a shift handover briefing for the incoming pharmacist.
Combines recent audit activity, current stock alerts, and patients due
for urgent refill into a structured clinical handover note.
"""

import anthropic
from datetime import datetime, timedelta
from tools.pharmacy_tools import (
    get_recent_audit_logs, get_low_stock_items,
    get_expiring_stock, get_patients_due_refill, log_audit_event,
)
from config import MODEL

SYSTEM_PROMPT = """You are generating a pharmacy shift handover note for the incoming pharmacist.

Write in NHS clinical handover style — structured, factual, scannable. No emojis.
Use plain section headers underlined with dashes.
Use 24-hour time (e.g. 14:30) and DD/MM/YYYY dates.
Prioritise: anything requiring immediate action goes first.

Sections to include:
1. Handover Summary — 2-3 sentences, overall pharmacy status for this shift
2. Pending Actions — anything started this shift that needs follow-up
3. Stock Alerts — critical low stock or expiring items needing action today
4. Patients to Watch — patients due for urgent refills or flagged in recent checks
5. Recent Interactions Flagged — any HIGH-risk interaction checks from this shift
6. Notes for Next Shift — anything else the incoming pharmacist needs to know

Be concise. This is a clinical handover document, not a narrative report."""


def _local_now():
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("Europe/London"))
    except Exception:
        return datetime.utcnow() + timedelta(hours=1)


def _fmt_logs(logs: list) -> str:
    if not logs:
        return "  No activity in the last 12 hours."
    return "\n".join(
        f"  [{l['timestamp'][11:16]}] {l['agent']} — {l['action']}: {l['details'][:90]}"
        for l in logs[:15]
    )


def _fmt_stock(items: list) -> str:
    if not items:
        return "  All items above reorder threshold."
    return "\n".join(
        f"  - {i['medication']}: {i['quantity']} units (threshold: {i['reorder_threshold']})"
        for i in items
    )


def _fmt_expiry(items: list) -> str:
    if not items:
        return "  No items expiring within 14 days."
    return "\n".join(
        f"  - {i['medication']}: expires {i['expiry_date']} "
        f"({i['quantity']} units, est. waste £{i['estimated_waste']})"
        for i in items
    )


def _fmt_patients(patients: list) -> str:
    if not patients:
        return "  No patients due in next 3 days."
    seen: set = set()
    lines = []
    for p in patients:
        if p["patient_id"] not in seen:
            seen.add(p["patient_id"])
            lines.append(
                f"  - {p['name']} (CHI: {p['nhs_number']}) — "
                f"{p['medication']} due {p['next_due_date']}"
            )
    return "\n".join(lines)


def generate_handover() -> dict:
    """Generate a shift handover note for the incoming pharmacist."""
    client = anthropic.Anthropic()
    now = _local_now()

    audit_logs = get_recent_audit_logs(limit=30)
    low_stock = get_low_stock_items()
    expiring = get_expiring_stock(days_ahead=14)
    patients_due = get_patients_due_refill(days_ahead=3)

    # Filter audit logs to last 12 hours
    cutoff = (now - timedelta(hours=12)).isoformat()[:19]
    recent_logs = [l for l in audit_logs if l["timestamp"][:19] >= cutoff]

    context = f"""Shift handover — {now.strftime('%d/%m/%Y  %H:%M')} BST

RECENT ACTIVITY (last 12 hours — {len(recent_logs)} entries):
{_fmt_logs(recent_logs)}

LOW STOCK ({len(low_stock)} items below threshold):
{_fmt_stock(low_stock)}

EXPIRING WITHIN 14 DAYS ({len(expiring)} items):
{_fmt_expiry(expiring)}

PATIENTS DUE FOR REFILL IN NEXT 3 DAYS ({len(patients_due)} patients):
{_fmt_patients(patients_due)}

Generate a structured handover note for the incoming pharmacist.
"""

    response = client.messages.create(
        model=MODEL,
        max_tokens=1000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": context}],
    )

    note = response.content[0].text

    log_audit_event(
        agent="HandoverAgent",
        action="HANDOVER_GENERATED",
        details=f"Shift handover at {now.strftime('%d/%m/%Y %H:%M')} BST | "
                f"Actions: {len(recent_logs)} | Low stock: {len(low_stock)} | "
                f"Patients due: {len(patients_due)}",
    )

    return {
        "generated_at": now.strftime("%d/%m/%Y  %H:%M"),
        "note": note,
        "context": {
            "recent_actions": len(recent_logs),
            "low_stock_items": len(low_stock),
            "expiring_items": len(expiring),
            "patients_due_urgent": len(set(p["patient_id"] for p in patients_due)),
        },
    }


if __name__ == "__main__":
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    print("=== Handover Agent ===\n")
    result = generate_handover()
    print(f"Generated at: {result['generated_at']}")
    print(f"Context: {result['context']}\n")
    print(result["note"])
