"""
PharmAgent AI — Test Suite
Run: pytest tests/ -v
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from db.database import init_db, SessionLocal
from db.models import Patient, Medication, StockItem, Prescription, AuditLog
from datetime import datetime, timedelta


@pytest.fixture(autouse=True)
def setup_db(tmp_path, monkeypatch):
    """Use an in-memory SQLite DB for every test."""
    import db.database as db_module
    db_module.DATABASE_URL = "sqlite:///:memory:"
    db_module.engine = __import__("sqlalchemy").create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    db_module.SessionLocal = __import__("sqlalchemy.orm", fromlist=["sessionmaker"]).sessionmaker(
        autocommit=False, autoflush=False, bind=db_module.engine
    )
    init_db()

    db = db_module.SessionLocal()
    med_warfarin = Medication(id=1, name="Warfarin 5mg", generic_name="warfarin",
                               category="Anticoagulant", unit="tablets",
                               interactions="aspirin,ibuprofen")
    med_aspirin = Medication(id=2, name="Aspirin 75mg", generic_name="aspirin",
                              category="Antiplatelet", unit="tablets",
                              interactions="warfarin,ibuprofen")
    med_metformin = Medication(id=3, name="Metformin 500mg", generic_name="metformin",
                                category="Antidiabetic", unit="tablets", interactions="")
    db.add_all([med_warfarin, med_aspirin, med_metformin])

    patient = Patient(id=1, nhs_number="1234567890", first_name="Test",
                      last_name="Patient", date_of_birth="1960-01-01",
                      phone="07700900000", email="test@test.com")
    db.add(patient)

    today = datetime.today()
    rx1 = Prescription(patient_id=1, medication_id=1, dosage="5mg",
                       frequency="Once daily", prescriber="Dr Test",
                       issue_date=today.strftime("%Y-%m-%d"),
                       next_due_date=(today + timedelta(days=3)).strftime("%Y-%m-%d"),
                       active=True)
    rx2 = Prescription(patient_id=1, medication_id=2, dosage="75mg",
                       frequency="Once daily", prescriber="Dr Test",
                       issue_date=today.strftime("%Y-%m-%d"),
                       next_due_date=(today + timedelta(days=3)).strftime("%Y-%m-%d"),
                       active=True)
    db.add_all([rx1, rx2])

    stock_low = StockItem(medication_id=1, quantity=15, reorder_threshold=50,
                          reorder_quantity=200,
                          expiry_date=(today + timedelta(days=365)).strftime("%Y-%m-%d"),
                          supplier="TestSupplier", unit_cost=0.10)
    stock_expiring = StockItem(medication_id=2, quantity=200, reorder_threshold=50,
                               reorder_quantity=200,
                               expiry_date=(today + timedelta(days=15)).strftime("%Y-%m-%d"),
                               supplier="TestSupplier", unit_cost=0.05)
    stock_ok = StockItem(medication_id=3, quantity=500, reorder_threshold=50,
                         reorder_quantity=200,
                         expiry_date=(today + timedelta(days=400)).strftime("%Y-%m-%d"),
                         supplier="TestSupplier", unit_cost=0.08)
    db.add_all([stock_low, stock_expiring, stock_ok])
    db.commit()
    db.close()
    yield


class TestToolLayer:
    def test_get_patient_by_nhs_found(self):
        from tools.pharmacy_tools import get_patient_by_nhs
        result = get_patient_by_nhs("1234567890")
        assert result["name"] == "Test Patient"
        assert result["nhs_number"] == "1234567890"

    def test_get_patient_by_nhs_not_found(self):
        from tools.pharmacy_tools import get_patient_by_nhs
        result = get_patient_by_nhs("0000000000")
        assert "error" in result

    def test_get_active_prescriptions(self):
        from tools.pharmacy_tools import get_active_prescriptions
        rxs = get_active_prescriptions(1)
        assert len(rxs) == 2
        names = [r["generic_name"] for r in rxs]
        assert "warfarin" in names
        assert "aspirin" in names

    def test_get_low_stock_items(self):
        from tools.pharmacy_tools import get_low_stock_items
        low = get_low_stock_items()
        assert len(low) == 1
        assert low[0]["medication"] == "Warfarin 5mg"
        assert low[0]["quantity"] == 15

    def test_get_expiring_stock(self):
        from tools.pharmacy_tools import get_expiring_stock
        expiring = get_expiring_stock(days_ahead=30)
        assert len(expiring) == 1
        assert expiring[0]["medication"] == "Aspirin 75mg"

    def test_get_patients_due_refill(self):
        from tools.pharmacy_tools import get_patients_due_refill
        due = get_patients_due_refill(days_ahead=7)
        assert len(due) >= 1
        assert due[0]["name"] == "Test Patient"

    def test_place_reorder(self):
        from tools.pharmacy_tools import place_reorder
        order = place_reorder("Warfarin 5mg", 200, "TestSupplier")
        assert order["status"] == "order_placed"
        assert order["quantity"] == 200
        assert "reference" in order

    def test_send_patient_message(self):
        from tools.pharmacy_tools import send_patient_message
        result = send_patient_message(1, "sms", "Hello Test, your prescription is due.")
        assert result["status"] == "sent"
        assert result["channel"] == "sms"

    def test_send_message_unknown_patient(self):
        from tools.pharmacy_tools import send_patient_message
        result = send_patient_message(9999, "sms", "Test")
        assert "error" in result

    def test_audit_log(self):
        from tools.pharmacy_tools import log_audit_event, get_recent_audit_logs
        log_audit_event("TestAgent", "TEST_ACTION", "Test details", patient_id=1)
        logs = get_recent_audit_logs(limit=5)
        assert any(l["action"] == "TEST_ACTION" for l in logs)


class TestInteractionSafetyAgent:
    def test_returns_string(self):
        from agents.interaction_safety_agent import check_interactions
        result = check_interactions("1234567890")
        assert isinstance(result, str)
        assert len(result) > 10

    def test_patient_not_found(self):
        from agents.interaction_safety_agent import check_interactions
        result = check_interactions("0000000000")
        assert "No patient found" in result or "error" in result.lower()

    def test_contains_medication_names(self):
        from agents.interaction_safety_agent import check_interactions
        result = check_interactions("1234567890")
        assert any(m in result.lower() for m in ["warfarin", "aspirin"])


class TestStockIntelligenceAgent:
    def test_returns_dict_with_analysis(self):
        from agents.stock_intelligence_agent import run_stock_review
        result = run_stock_review()
        assert isinstance(result, dict)
        assert "analysis" in result
        assert isinstance(result["analysis"], str)

    def test_detects_low_stock(self):
        from agents.stock_intelligence_agent import run_stock_review
        result = run_stock_review()
        assert result["low_stock_count"] == 1

    def test_detects_expiring(self):
        from agents.stock_intelligence_agent import run_stock_review
        result = run_stock_review()
        assert result["expiring_count"] == 1

    def test_auto_orders_critical_low_stock(self):
        from agents.stock_intelligence_agent import run_stock_review
        result = run_stock_review()
        assert len(result["orders_placed"]) >= 1


class TestPatientEngagementAgent:
    def test_returns_dict(self):
        from agents.patient_engagement_agent import run_engagement_campaign
        result = run_engagement_campaign(days_ahead=7, channel="sms")
        assert isinstance(result, dict)
        assert "patients_contacted" in result

    def test_contacts_due_patients(self):
        from agents.patient_engagement_agent import run_engagement_campaign
        result = run_engagement_campaign(days_ahead=7, channel="sms")
        assert result["patients_contacted"] >= 1

    def test_message_content(self):
        from agents.patient_engagement_agent import run_engagement_campaign
        result = run_engagement_campaign(days_ahead=7, channel="sms")
        if result["results"]:
            msg = result["results"][0]["message"]
            assert isinstance(msg, str)
            assert len(msg) > 10

    def test_no_patients_outside_window(self):
        from agents.patient_engagement_agent import run_engagement_campaign
        result = run_engagement_campaign(days_ahead=0, channel="sms")
        assert result["patients_contacted"] == 0
