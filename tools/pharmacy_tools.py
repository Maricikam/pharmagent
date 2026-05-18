"""
Tool Layer — deterministic functions for PharmAgent AI.
These are the 'classic software' components: predictable, auditable, testable.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.database import SessionLocal
from db.models import Patient, Medication, StockItem, Prescription, AuditLog
from datetime import datetime, timedelta
import json


def _db():
    return SessionLocal()


# ── PATIENT TOOLS ─────────────────────────────────────────────────────────────

def get_patient_by_nhs(nhs_number: str) -> dict:
    db = _db()
    p = db.query(Patient).filter(Patient.nhs_number == nhs_number).first()
    db.close()
    if not p:
        return {"error": f"No patient found with NHS number {nhs_number}"}
    return {
        "id": p.id,
        "nhs_number": p.nhs_number,
        "name": f"{p.first_name} {p.last_name}",
        "date_of_birth": p.date_of_birth,
        "phone": p.phone,
        "email": p.email,
    }


def get_active_prescriptions(patient_id: int) -> list[dict]:
    db = _db()
    rxs = (db.query(Prescription)
           .filter(Prescription.patient_id == patient_id, Prescription.active == True)
           .all())
    result = []
    for rx in rxs:
        result.append({
            "id": rx.id,
            "medication": rx.medication.name,
            "generic_name": rx.medication.generic_name,
            "dosage": rx.dosage,
            "frequency": rx.frequency,
            "prescriber": rx.prescriber,
            "next_due_date": rx.next_due_date,
            "known_interactions": rx.medication.interactions,
        })
    db.close()
    return result


def get_patients_due_refill(days_ahead: int = 7) -> list[dict]:
    """Return patients whose prescriptions are due within the next N days."""
    db = _db()
    cutoff = (datetime.today() + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
    today = datetime.today().strftime("%Y-%m-%d")
    rxs = (db.query(Prescription)
           .filter(Prescription.active == True,
                   Prescription.next_due_date <= cutoff,
                   Prescription.next_due_date >= today)
           .all())
    result = []
    seen = set()
    for rx in rxs:
        if rx.patient_id not in seen:
            seen.add(rx.patient_id)
            result.append({
                "patient_id": rx.patient_id,
                "nhs_number": rx.patient.nhs_number,
                "name": f"{rx.patient.first_name} {rx.patient.last_name}",
                "phone": rx.patient.phone,
                "email": rx.patient.email,
                "next_due_date": rx.next_due_date,
                "medication": rx.medication.name,
            })
    db.close()
    return result


# ── STOCK TOOLS ───────────────────────────────────────────────────────────────

def get_all_stock() -> list[dict]:
    db = _db()
    items = db.query(StockItem).all()
    result = []
    for item in items:
        result.append({
            "id": item.id,
            "medication": item.medication.name,
            "generic_name": item.medication.generic_name,
            "quantity": item.quantity,
            "reorder_threshold": item.reorder_threshold,
            "reorder_quantity": item.reorder_quantity,
            "expiry_date": item.expiry_date,
            "supplier": item.supplier,
            "unit_cost": item.unit_cost,
            "below_threshold": item.quantity < item.reorder_threshold,
        })
    db.close()
    return result


def get_low_stock_items() -> list[dict]:
    return [item for item in get_all_stock() if item["below_threshold"]]


def get_expiring_stock(days_ahead: int = 30) -> list[dict]:
    db = _db()
    cutoff = (datetime.today() + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
    today = datetime.today().strftime("%Y-%m-%d")
    items = (db.query(StockItem)
             .filter(StockItem.expiry_date <= cutoff,
                     StockItem.expiry_date >= today)
             .all())
    result = []
    for item in items:
        result.append({
            "id": item.id,
            "medication": item.medication.name,
            "quantity": item.quantity,
            "expiry_date": item.expiry_date,
            "supplier": item.supplier,
            "unit_cost": item.unit_cost,
            "estimated_waste": round(item.quantity * item.unit_cost, 2),
        })
    db.close()
    return result


def place_reorder(medication_name: str, quantity: int, supplier: str) -> dict:
    """Simulate placing a reorder — logs the action, returns confirmation."""
    log_audit_event(
        agent="StockIntelligenceAgent",
        action="REORDER_PLACED",
        details=f"Reorder: {quantity} units of {medication_name} from {supplier}",
    )
    return {
        "status": "order_placed",
        "medication": medication_name,
        "quantity": quantity,
        "supplier": supplier,
        "estimated_delivery": (datetime.today() + timedelta(days=2)).strftime("%Y-%m-%d"),
        "reference": f"PO-{datetime.today().strftime('%Y%m%d')}-{abs(hash(medication_name)) % 9999:04d}",
    }


# ── MESSAGING TOOLS ───────────────────────────────────────────────────────────

def send_patient_message(patient_id: int, channel: str, message: str) -> dict:
    """
    Simulate sending a patient message.
    In production this would call Twilio or NHS Notify.
    Logs to audit trail instead of actually sending.
    """
    db = _db()
    p = db.query(Patient).filter(Patient.id == patient_id).first()
    db.close()

    if not p:
        return {"error": f"Patient {patient_id} not found"}

    recipient = p.email if channel == "email" else p.phone
    log_audit_event(
        agent="PatientEngagementAgent",
        action="MESSAGE_SENT",
        details=f"Channel: {channel} | To: {recipient} | Message: {message[:100]}...",
        patient_id=patient_id,
    )
    return {
        "status": "sent",
        "patient": f"{p.first_name} {p.last_name}",
        "channel": channel,
        "recipient": recipient,
        "message_preview": message[:80],
        "timestamp": datetime.utcnow().isoformat(),
    }


# ── AUDIT TOOLS ───────────────────────────────────────────────────────────────

def log_audit_event(agent: str, action: str, details: str, patient_id: int = None):
    db = _db()
    log = AuditLog(agent=agent, action=action, details=details, patient_id=patient_id)
    db.add(log)
    db.commit()
    db.close()


def get_recent_audit_logs(limit: int = 20) -> list[dict]:
    db = _db()
    logs = (db.query(AuditLog)
            .order_by(AuditLog.timestamp.desc())
            .limit(limit)
            .all())
    result = [{"timestamp": l.timestamp.isoformat(), "agent": l.agent,
               "action": l.action, "details": l.details} for l in logs]
    db.close()
    return result