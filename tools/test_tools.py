"""
tests/test_tools.py — Unit tests for the tool layer.

Run with: pytest tests/ -v
All tests use an in-memory SQLite DB (no external dependencies needed).
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Use in-memory SQLite for tests
os.environ["DATABASE_URL"] = "sqlite:///./test_pharmagent.db"

from db.session import init_db, SessionLocal
from db.models import Patient, Medication, Prescription, StockItem
from tools.pharmacy_tools import (
    get_patient_by_nhs,
    get_active_prescriptions,
    get_medication_by_name,
    get_low_stock_items,
    get_near_expiry_items,
    log_agent_action,
    get_audit_log,
    create_supplier_order,
)
import json
from datetime import datetime, timedelta


@pytest.fixture(autouse=True)
def setup_db():
    """Fresh DB for every test."""
    init_db()
    db = SessionLocal()
    db.query(StockItem).delete()
    db.query(Prescription).delete()
    db.query(Patient).delete()
    db.query(Medication).delete()
    db.commit()

    # Seed test data
    med_warfarin = Medication(name="Warfarin 5mg", generic_name="warfarin",
                               drug_class="anticoagulant",
                               contraindications=json.dumps(["NSAID", "antiplatelet"]))
    med_ibuprofen = Medication(name="Ibuprofen 400mg", generic_name="ibuprofen",
                                drug_class="NSAID",
                                contraindications=json.dumps(["anticoagulant"]))
    med_atorvastatin = Medication(name="Atorvastatin 20mg", generic_name="atorvastatin",
                                   drug_class="statin", contraindications=json.dumps([]))
    db.add_all([med_warfarin, med_ibuprofen, med_atorvastatin])
    db.commit()

    patient = Patient(nhs_number="1234567890", first_name="Test", last_name="Patient",
                       date_of_birth="1960-01-01", phone="07700900000", email="test@example.com")
    db.add(patient)
    db.commit()

    prescription = Prescription(
        patient_id=patient.id, medication_id=med_warfarin.id,
        dosage="5mg", frequency="Once daily", start_date="2025-01-01",
        end_date="2026-12-31", is_active=True, prescribed_by="Dr Test"
    )
    db.add(prescription)

    stock_low = StockItem(medication_id=med_warfarin.id, quantity=20, reorder_threshold=50,
                           expiry_date=(datetime.today() + timedelta(days=200)).strftime("%Y-%m-%d"),
                           batch_number="B001", supplier="AAH", unit_cost=0.12)
    stock_ok = StockItem(medication_id=med_atorvastatin.id, quantity=200, reorder_threshold=50,
                          expiry_date=(datetime.today() + timedelta(days=365)).strftime("%Y-%m-%d"),
                          batch_number="B002", supplier="Sigma", unit_cost=0.45)
    stock_expiring = StockItem(medication_id=med_ibuprofen.id, quantity=100, reorder_threshold=50,
                                expiry_date=(datetime.today() + timedelta(days=10)).strftime("%Y-%m-%d"),
                                batch_number="B003", supplier="Phoenix", unit_cost=0.05)
    db.add_all([stock_low, stock_ok, stock_expiring])
    db.commit()
    db.close()
    yield


# ── Patient tool tests ────────────────────────────────────────────────────────

def test_get_patient_by_nhs_found():
    result = get_patient_by_nhs("1234567890")
    assert result["name"] == "Test Patient"
    assert result["nhs_number"] == "1234567890"


def test_get_patient_by_nhs_not_found():
    result = get_patient_by_nhs("0000000000")
    assert "error" in result


def test_get_active_prescriptions():
    patient = get_patient_by_nhs("1234567890")
    result = get_active_prescriptions(patient["id"])
    assert result["count"] == 1
    assert result["active_prescriptions"][0]["medication_name"] == "Warfarin 5mg"
    assert result["active_prescriptions"][0]["drug_class"] == "anticoagulant"


def test_get_active_prescriptions_contraindications():
    patient = get_patient_by_nhs("1234567890")
    result = get_active_prescriptions(patient["id"])
    rxs = result["active_prescriptions"]
    assert "NSAID" in rxs[0]["contraindications"]


# ── Medication tool tests ─────────────────────────────────────────────────────

def test_get_medication_by_name_found():
    result = get_medication_by_name("Warfarin")
    assert result["drug_class"] == "anticoagulant"
    assert "NSAID" in result["contraindications"]


def test_get_medication_by_name_not_found():
    result = get_medication_by_name("NonExistentDrug")
    assert "error" in result


def test_get_medication_no_contraindications():
    result = get_medication_by_name("Atorvastatin")
    assert result["contraindications"] == []


# ── Stock tool tests ──────────────────────────────────────────────────────────

def test_get_low_stock_items():
    result = get_low_stock_items()
    names = [i["medication_name"] for i in result["low_stock_items"]]
    assert "Warfarin 5mg" in names
    assert "Atorvastatin 20mg" not in names


def test_get_near_expiry_items():
    result = get_near_expiry_items(days_window=30)
    names = [i["medication_name"] for i in result["expiring_items"]]
    assert "Ibuprofen 400mg" in names
    assert "Atorvastatin 20mg" not in names


def test_get_near_expiry_items_days_remaining():
    result = get_near_expiry_items(days_window=30)
    expiring = result["expiring_items"]
    ibu = next(i for i in expiring if i["medication_name"] == "Ibuprofen 400mg")
    assert ibu["days_until_expiry"] <= 30


# ── Audit log tests ───────────────────────────────────────────────────────────

def test_log_agent_action():
    result = log_agent_action(
        agent_name="InteractionSafetyAgent",
        action="interaction_check",
        details="Checked Warfarin vs Ibuprofen — HIGH RISK",
        patient_id=1
    )
    assert result["logged"] is True


def test_get_audit_log():
    log_agent_action("TestAgent", "test_action", "test details")
    result = get_audit_log(limit=10)
    assert result["count"] >= 1
    assert result["entries"][0]["agent"] == "TestAgent"


# ── Supplier order tests ──────────────────────────────────────────────────────

def test_create_supplier_order():
    db = SessionLocal()
    med = db.query(Medication).filter(Medication.name == "Warfarin 5mg").first()
    med_id = med.id
    db.close()

    result = create_supplier_order(medication_id=med_id, supplier="AAH Pharmaceuticals", quantity=200)
    assert result["status"] == "pending"
    assert result["quantity_ordered"] == 200
    assert "order_id" in result
