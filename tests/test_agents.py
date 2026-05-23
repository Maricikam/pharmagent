"""
PharmAgent AI — Test Suite
Run: pytest tests/ -v
"""
import pytest
from unittest.mock import patch, MagicMock, call
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


def _make_mock_anthropic(response_text: str):
    """Return a patched anthropic.Anthropic whose messages.create returns response_text."""
    mock_client = MagicMock()
    mock_client.messages.create.return_value = MagicMock(
        content=[MagicMock(text=response_text)]
    )
    return MagicMock(return_value=mock_client)


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
    _MOCK_REPORT = (
        "# INTERACTION SAFETY ASSESSMENT\n"
        "**Patient:** Test Patient (DOB: 1960-01-01) | **CHI:** 1234567890\n"
        "---\n"
        "## ACTIVE MEDICATIONS\n"
        "1. Warfarin 5mg — Once daily\n"
        "2. Aspirin 75mg — Once daily\n"
        "---\n"
        "## INTERACTION ANALYSIS\n"
        "| Drug Pair | Severity | Clinical Rationale |\n"
        "|---|---|---|\n"
        "| Warfarin + Ibuprofen | HIGH | NSAID displaces warfarin; major bleed risk |\n"
        "---\n"
        "## RECOMMENDATION\n"
        "⛔ **DO NOT DISPENSE WITHOUT CONSULTATION**\n"
        "**Actions before dispensing:**\n"
        "- Contact prescriber immediately\n\n"
        "**Status:** HIGH risk — pharmacist review required before dispensing."
    )

    @patch("anthropic.Anthropic")
    def test_returns_string(self, mock_anthropic):
        mock_anthropic.return_value.messages.create.return_value = MagicMock(
            content=[MagicMock(text=self._MOCK_REPORT)]
        )
        from agents.interaction_safety_agent import check_interactions
        result = check_interactions("1234567890")
        assert isinstance(result, str)
        assert len(result) > 10

    @patch("anthropic.Anthropic")
    def test_patient_not_found(self, mock_anthropic):
        mock_anthropic.return_value.messages.create.return_value = MagicMock(
            content=[MagicMock(text=self._MOCK_REPORT)]
        )
        from agents.interaction_safety_agent import check_interactions
        result = check_interactions("0000000000")
        assert "No patient found" in result or "error" in result.lower()

    @patch("anthropic.Anthropic")
    def test_contains_medication_names(self, mock_anthropic):
        mock_anthropic.return_value.messages.create.return_value = MagicMock(
            content=[MagicMock(text=self._MOCK_REPORT)]
        )
        from agents.interaction_safety_agent import check_interactions
        result = check_interactions("1234567890")
        assert any(m in result.lower() for m in ["warfarin", "aspirin"])

    @patch("anthropic.Anthropic")
    def test_high_risk_detected(self, mock_anthropic):
        mock_anthropic.return_value.messages.create.return_value = MagicMock(
            content=[MagicMock(text=self._MOCK_REPORT)]
        )
        from agents.interaction_safety_agent import check_interactions
        result = check_interactions("1234567890", "Ibuprofen")
        assert "HIGH" in result or "DO NOT" in result


class TestStockIntelligenceAgent:
    _MOCK_ANALYSIS = (
        "## Stock Review\n\n"
        "**IMMEDIATE ACTION REQUIRED:**\n"
        "- REORDER Warfarin 5mg | 200 units | TestSupplier\n\n"
        "**Near Expiry:**\n"
        "- Aspirin 75mg — expires in 15 days. Consider discounting.\n\n"
        "**Priority:** Reorder Warfarin today."
    )

    @patch("anthropic.Anthropic")
    def test_returns_dict_with_analysis(self, mock_anthropic):
        mock_anthropic.return_value.messages.create.return_value = MagicMock(
            content=[MagicMock(text=self._MOCK_ANALYSIS)]
        )
        from agents.stock_intelligence_agent import run_stock_review
        result = run_stock_review()
        assert isinstance(result, dict)
        assert "analysis" in result
        assert isinstance(result["analysis"], str)

    @patch("anthropic.Anthropic")
    def test_detects_low_stock(self, mock_anthropic):
        mock_anthropic.return_value.messages.create.return_value = MagicMock(
            content=[MagicMock(text=self._MOCK_ANALYSIS)]
        )
        from agents.stock_intelligence_agent import run_stock_review
        result = run_stock_review()
        assert result["low_stock_count"] == 1

    @patch("anthropic.Anthropic")
    def test_detects_expiring(self, mock_anthropic):
        mock_anthropic.return_value.messages.create.return_value = MagicMock(
            content=[MagicMock(text=self._MOCK_ANALYSIS)]
        )
        from agents.stock_intelligence_agent import run_stock_review
        result = run_stock_review()
        assert result["expiring_count"] == 1

    @patch("anthropic.Anthropic")
    def test_auto_orders_critical_low_stock(self, mock_anthropic):
        mock_anthropic.return_value.messages.create.return_value = MagicMock(
            content=[MagicMock(text=self._MOCK_ANALYSIS)]
        )
        from agents.stock_intelligence_agent import run_stock_review
        result = run_stock_review()
        assert len(result["orders_placed"]) >= 1


class TestPatientEngagementAgent:
    _MOCK_MESSAGE = (
        "Hi Test, your Warfarin 5mg prescription is due in 3 days. "
        "Please call Renfrew Road Pharmacy on 0141 555 0199."
    )

    @patch("anthropic.Anthropic")
    def test_returns_dict(self, mock_anthropic):
        mock_anthropic.return_value.messages.create.return_value = MagicMock(
            content=[MagicMock(text=self._MOCK_MESSAGE)]
        )
        from agents.patient_engagement_agent import run_engagement_campaign
        result = run_engagement_campaign(days_ahead=7, channel="sms")
        assert isinstance(result, dict)
        assert "patients_contacted" in result

    @patch("anthropic.Anthropic")
    def test_contacts_due_patients(self, mock_anthropic):
        mock_anthropic.return_value.messages.create.return_value = MagicMock(
            content=[MagicMock(text=self._MOCK_MESSAGE)]
        )
        from agents.patient_engagement_agent import run_engagement_campaign
        result = run_engagement_campaign(days_ahead=7, channel="sms")
        assert result["patients_contacted"] >= 1

    @patch("anthropic.Anthropic")
    def test_message_content(self, mock_anthropic):
        mock_anthropic.return_value.messages.create.return_value = MagicMock(
            content=[MagicMock(text=self._MOCK_MESSAGE)]
        )
        from agents.patient_engagement_agent import run_engagement_campaign
        result = run_engagement_campaign(days_ahead=7, channel="sms")
        if result["results"]:
            msg = result["results"][0]["message"]
            assert isinstance(msg, str)
            assert len(msg) > 10

    @patch("anthropic.Anthropic")
    def test_no_patients_outside_window(self, mock_anthropic):
        mock_anthropic.return_value.messages.create.return_value = MagicMock(
            content=[MagicMock(text=self._MOCK_MESSAGE)]
        )
        from agents.patient_engagement_agent import run_engagement_campaign
        result = run_engagement_campaign(days_ahead=0, channel="sms")
        assert result["patients_contacted"] == 0


class TestOrchestratorAgent:
    """
    Tests the agentic loop: Claude returns tool_use → tools execute →
    results fed back → Claude returns final text.
    """

    def _make_tool_block(self, name, tool_id, input_data=None):
        block = MagicMock()
        block.type = "tool_use"
        block.name = name
        block.input = input_data or {}
        block.id = tool_id
        return block

    def _make_text_response(self, text):
        text_block = MagicMock()
        text_block.type = "text"
        text_block.text = text
        response = MagicMock()
        response.stop_reason = "end_turn"
        response.content = [text_block]
        return response

    @patch("agents.orchestrator_agent.run_stock_review")
    @patch("agents.orchestrator_agent.client")
    def test_routes_stock_request_to_stock_agent(self, mock_client, mock_stock):
        mock_stock.return_value = {"analysis": "5 items low", "orders_placed": []}

        tool_response = MagicMock()
        tool_response.stop_reason = "tool_use"
        tool_response.content = [self._make_tool_block("run_stock_review", "tu_001")]

        final_response = self._make_text_response("Stock review complete. 5 items need reordering.")
        mock_client.messages.create.side_effect = [tool_response, final_response]

        from agents.orchestrator_agent import run_orchestrator
        result = run_orchestrator("What's running low on stock?")

        assert isinstance(result, str)
        assert len(result) > 0
        mock_stock.assert_called_once()
        assert mock_client.messages.create.call_count == 2

    @patch("agents.orchestrator_agent.run_engagement_campaign")
    @patch("agents.orchestrator_agent.run_stock_review")
    @patch("agents.orchestrator_agent.client")
    def test_morning_briefing_calls_multiple_agents(self, mock_client, mock_stock, mock_engagement):
        mock_stock.return_value = {"analysis": "All good", "orders_placed": []}
        mock_engagement.return_value = {"patients_contacted": 3, "results": []}

        stock_block = self._make_tool_block("run_stock_review", "tu_001")
        engagement_block = self._make_tool_block("run_patient_engagement", "tu_002", {"days_ahead": 7, "channel": "sms"})

        tool_response = MagicMock()
        tool_response.stop_reason = "tool_use"
        tool_response.content = [stock_block, engagement_block]

        final_response = self._make_text_response("Morning briefing complete. Stock healthy. 3 patients contacted.")
        mock_client.messages.create.side_effect = [tool_response, final_response]

        from agents.orchestrator_agent import run_orchestrator
        result = run_orchestrator("Good morning, run the daily pharmacy check.")

        assert isinstance(result, str)
        mock_stock.assert_called_once()
        mock_engagement.assert_called_once()

    @patch("agents.orchestrator_agent.client")
    def test_respects_max_turns_guard(self, mock_client):
        """Orchestrator must not loop indefinitely if Claude keeps requesting tools."""
        tool_response = MagicMock()
        tool_response.stop_reason = "tool_use"
        tool_response.content = []

        # Always return tool_use — guard must break the loop
        mock_client.messages.create.return_value = tool_response

        from agents.orchestrator_agent import run_orchestrator, MAX_TURNS
        result = run_orchestrator("Loop me forever.")

        assert mock_client.messages.create.call_count <= MAX_TURNS + 1

    @patch("agents.orchestrator_agent.client")
    def test_returns_string(self, mock_client):
        mock_client.messages.create.return_value = self._make_text_response(
            "No urgent issues. All systems normal."
        )
        from agents.orchestrator_agent import run_orchestrator
        result = run_orchestrator("Quick status check.")
        assert isinstance(result, str)
        assert len(result) > 0
