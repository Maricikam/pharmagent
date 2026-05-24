"""
Tool Layer — deterministic functions for PharmAgent AI.
These are the 'classic software' components: predictable, auditable, testable.
"""
from db.database import SessionLocal
from db.models import Patient, Medication, StockItem, Prescription, AuditLog
from datetime import datetime, timedelta
import json


def _db():
    return SessionLocal()


# ── PATIENT TOOLS ─────────────────────────────────────────────────────────────

def get_patient_by_nhs(nhs_number: str) -> dict:
    db = _db()
    try:
        p = db.query(Patient).filter(Patient.nhs_number == nhs_number).first()
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
    finally:
        db.close()


def get_patient_by_name(name: str) -> list[dict]:
    """Search patients by name (case-insensitive, partial match per word)."""
    db = _db()
    try:
        from sqlalchemy import func
        terms = name.strip().lower().split()
        query = db.query(Patient)
        for term in terms:
            query = query.filter(
                func.lower(Patient.first_name).contains(term) |
                func.lower(Patient.last_name).contains(term)
            )
        return [
            {
                "id": p.id,
                "nhs_number": p.nhs_number,
                "name": f"{p.first_name} {p.last_name}",
                "date_of_birth": p.date_of_birth,
            }
            for p in query.all()
        ]
    finally:
        db.close()


def get_active_prescriptions(patient_id: int) -> list[dict]:
    db = _db()
    try:
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
        return result
    finally:
        db.close()


def get_patients_due_refill(days_ahead: int = 7) -> list[dict]:
    """Return patients whose prescriptions are due within the next N days."""
    db = _db()
    try:
        cutoff = (datetime.today() + timedelta(days=int(days_ahead))).strftime("%Y-%m-%d")
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
        return result
    finally:
        db.close()


# ── STOCK TOOLS ───────────────────────────────────────────────────────────────

def get_all_stock() -> list[dict]:
    db = _db()
    try:
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
        return result
    finally:
        db.close()


def get_low_stock_items() -> list[dict]:
    return [item for item in get_all_stock() if item["below_threshold"]]


def get_expiring_stock(days_ahead: int = 30) -> list[dict]:
    db = _db()
    try:
        cutoff = (datetime.today() + timedelta(days=int(days_ahead))).strftime("%Y-%m-%d")
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
        return result
    finally:
        db.close()


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


def dispose_stock(medication_name: str, action: str, quantity: int, expiry_date: str) -> dict:
    """Log a stock disposal or supplier return for an expiring item."""
    action_label = "STOCK_RETURNED" if action == "return" else "STOCK_DISPOSED"
    action_text = "Returned to supplier" if action == "return" else "Disposed (expired/near-expiry)"
    log_audit_event(
        agent="StockIntelligenceAgent",
        action=action_label,
        details=f"{action_text}: {quantity} units of {medication_name} (expiry: {expiry_date})",
    )
    ref = f"DISP-{datetime.today().strftime('%Y%m%d')}-{abs(hash(medication_name)) % 9999:04d}"
    return {
        "status": "logged",
        "medication": medication_name,
        "action": action_text,
        "quantity": quantity,
        "expiry_date": expiry_date,
        "reference": ref,
    }


# ── MESSAGING TOOLS ───────────────────────────────────────────────────────────

def send_patient_message(patient_id: int, channel: str, message: str) -> dict:
    """
    Simulate sending a patient message.
    In production this would call Twilio or NHS Notify.
    Logs to audit trail instead of actually sending.
    """
    db = _db()
    try:
        p = db.query(Patient).filter(Patient.id == patient_id).first()
        if not p:
            return {"error": f"Patient {patient_id} not found"}
        patient_name = f"{p.first_name} {p.last_name}"
        recipient = p.email if channel == "email" else p.phone
    finally:
        db.close()

    log_audit_event(
        agent="PatientEngagementAgent",
        action="MESSAGE_SENT",
        details=f"Channel: {channel} | To: {recipient} | Message: {message[:100]}...",
        patient_id=patient_id,
    )
    return {
        "status": "sent",
        "patient": patient_name,
        "channel": channel,
        "recipient": recipient,
        "message_preview": message[:80],
        "timestamp": datetime.utcnow().isoformat(),
    }


# ── AUDIT TOOLS ───────────────────────────────────────────────────────────────

def log_audit_event(agent: str, action: str, details: str, patient_id: int = None):
    db = _db()
    try:
        log = AuditLog(agent=agent, action=action, details=details, patient_id=patient_id)
        db.add(log)
        db.commit()
    finally:
        db.close()


def get_recent_audit_logs(limit: int = 20) -> list[dict]:
    db = _db()
    try:
        logs = (db.query(AuditLog)
                .order_by(AuditLog.timestamp.desc())
                .limit(limit)
                .all())
        return [{"timestamp": l.timestamp.isoformat(), "agent": l.agent,
                 "action": l.action, "details": l.details} for l in logs]
    finally:
        db.close()


# ── ANALYTICS TOOLS ───────────────────────────────────────────────────────────

def get_workload_preview(days: int = 7) -> list[dict]:
    """Count prescriptions due per day for the next N days."""
    db = _db()
    try:
        today = datetime.today()
        result = []
        for i in range(days):
            day = (today + timedelta(days=i)).strftime("%Y-%m-%d")
            day_label = (today + timedelta(days=i)).strftime("%A %d/%m")
            count = (db.query(Prescription)
                     .filter(Prescription.active == True,
                             Prescription.next_due_date == day)
                     .count())
            result.append({
                "date": day,
                "day_label": day_label,
                "prescriptions_due": count,
            })
        return result
    finally:
        db.close()


def get_prescription_demand() -> list[dict]:
    """Count active prescriptions per medication — proxy for daily demand and days of supply."""
    db = _db()
    try:
        from db.models import Medication
        meds = db.query(Medication).all()
        result = []
        for med in meds:
            count = (db.query(Prescription)
                     .filter(Prescription.medication_id == med.id, Prescription.active == True)
                     .count())
            if count == 0:
                continue
            stock = db.query(StockItem).filter(StockItem.medication_id == med.id).first()
            current_stock = stock.quantity if stock else None
            reorder_threshold = stock.reorder_threshold if stock else None
            days_of_supply = round(current_stock / count, 1) if current_stock is not None else None
            result.append({
                "medication_id": med.id,
                "medication": med.name,
                "active_prescriptions": count,
                "estimated_monthly_units": count * 30,
                "current_stock": current_stock,
                "reorder_threshold": reorder_threshold,
                "days_of_supply": days_of_supply,
                "smart_reorder_quantity": count * 60,  # 2-month buffer
            })
        return sorted(result, key=lambda x: (x.get("days_of_supply") or 9999))
    finally:
        db.close()


def get_overdue_patients() -> list[dict]:
    """Return patients with active prescriptions past their next_due_date."""
    db = _db()
    try:
        today = datetime.today()
        today_str = today.strftime("%Y-%m-%d")
        rxs = (db.query(Prescription)
               .filter(Prescription.active == True,
                       Prescription.next_due_date < today_str)
               .all())
        seen = set()
        result = []
        for rx in rxs:
            if rx.patient_id in seen:
                continue
            seen.add(rx.patient_id)
            try:
                due = datetime.strptime(rx.next_due_date, "%Y-%m-%d")
                days_overdue = (today - due).days
            except Exception:
                days_overdue = 0
            result.append({
                "patient_id": rx.patient_id,
                "nhs_number": rx.patient.nhs_number,
                "name": f"{rx.patient.first_name} {rx.patient.last_name}",
                "phone": rx.patient.phone,
                "email": rx.patient.email,
                "next_due_date": rx.next_due_date,
                "days_overdue": days_overdue,
                "medication": rx.medication.name,
            })
        return sorted(result, key=lambda x: x["days_overdue"], reverse=True)
    finally:
        db.close()


def get_anomaly_signals() -> dict:
    """Detect unusual patterns across stock, prescriptions, and audit logs."""
    db = _db()
    try:
        from sqlalchemy import func
        seven_days_ago = (datetime.today() - timedelta(days=7)).isoformat()

        overdue = get_overdue_patients()

        polypharmacy_rows = (
            db.query(Prescription.patient_id, func.count(Prescription.id).label("cnt"))
            .filter(Prescription.active == True)
            .group_by(Prescription.patient_id)
            .having(func.count(Prescription.id) >= 5)
            .all()
        )
        polypharmacy_patients = []
        for pid, cnt in polypharmacy_rows:
            p = db.query(Patient).filter(Patient.id == pid).first()
            if p:
                polypharmacy_patients.append({
                    "patient_id": pid,
                    "name": f"{p.first_name} {p.last_name}",
                    "nhs_number": p.nhs_number,
                    "active_prescriptions": cnt,
                })

        recent_emergency = (
            db.query(AuditLog)
            .filter(AuditLog.action == "EMERGENCY_SUPPLY",
                    AuditLog.timestamp >= seven_days_ago)
            .count()
        )

        demand = get_prescription_demand()
        shortage_risk = [
            d for d in demand
            if d.get("days_of_supply") is not None and d["days_of_supply"] < 14
        ]

        return {
            "overdue_patients": len(overdue),
            "overdue_details": overdue[:5],
            "polypharmacy_patients": len(polypharmacy_patients),
            "polypharmacy_details": polypharmacy_patients,
            "recent_emergency_supplies": recent_emergency,
            "shortage_risk_items": shortage_risk,
        }
    finally:
        db.close()