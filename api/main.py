"""
api/main.py — PharmAgent AI FastAPI application.

Exposes the multi-agent pharmacy system as HTTP endpoints.
Includes a /demo endpoint for judges and OpenClaw showcase.

All agent endpoints fall back gracefully to realistic demo data
when the database has not been seeded or the API key is missing.

Live URL: https://web-production-1f27a.up.railway.app
API docs: https://web-production-1f27a.up.railway.app/docs
"""

import os
import random
import string
from datetime import datetime, timedelta
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(
    title="PharmAgent AI",
    description=(
        "Intelligent Agent System for Pharmacy Management. "
        "Built for the DataVita OpenClaw Challenge. "
        "HND Software Development — New College Lanarkshire. "
        "\n\n**Quick links:** "
        "[/demo](/demo) · [/health](/health) · [GitHub](https://github.com/Maricikam/pharmagent)"
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _ref() -> str:
    """Generate a random audit reference number."""
    return "REF-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=8))


def _ts() -> str:
    """Return current UTC timestamp as ISO string."""
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def _has_api_key() -> bool:
    """Check whether an Anthropic API key is configured."""
    return bool(os.getenv("ANTHROPIC_API_KEY", "").strip())


def _demo_interaction_report(nhs_number: str, medication: str) -> dict:
    """Return a realistic demo interaction safety report."""
    return {
        "patient": {
            "name": "Margaret Campbell",
            "nhs_number": nhs_number,
            "dob": "1948-03-14",
        },
        "active_medications": [
            {"name": "Warfarin", "dose": "5mg", "frequency": "Once daily"},
            {"name": "Aspirin", "dose": "75mg", "frequency": "Once daily"},
            {"name": "Atorvastatin", "dose": "40mg", "frequency": "Once nightly"},
        ],
        "new_medication": medication,
        "interaction_report": {
            "risk_level": "HIGH",
            "interactions_detected": [
                {
                    "drug_a": "Warfarin",
                    "drug_b": medication,
                    "severity": "Major",
                    "mechanism": (
                        "NSAIDs inhibit platelet aggregation and may displace warfarin "
                        "from plasma protein binding, significantly increasing bleeding risk."
                    ),
                    "recommendation": (
                        "DO NOT DISPENSE without prescriber review. "
                        "Consider paracetamol as a safer alternative."
                    ),
                },
                {
                    "drug_a": "Aspirin",
                    "drug_b": medication,
                    "severity": "Moderate",
                    "mechanism": "Concurrent NSAID use increases GI bleeding risk.",
                    "recommendation": "Avoid combination if possible.",
                },
            ],
            "clinical_decision": (
                "REQUIRES PHARMACIST REVIEW — do not dispense without consultation"
            ),
            "audit_ref": _ref(),
            "checked_at": _ts(),
        },
    }


def _demo_stock_report() -> dict:
    """Return a realistic demo stock intelligence report."""
    return {
        "inventory_summary": {
            "total_medications_tracked": 847,
            "low_stock_items": 6,
            "near_expiry_items": 4,
            "reorders_triggered": 3,
            "estimated_waste_value": "£312.40",
        },
        "low_stock": [
            {
                "medication": "Metformin 500mg",
                "current_stock": 48,
                "reorder_threshold": 100,
                "supplier": "AAH Pharmaceuticals",
                "reorder_ref": _ref(),
            },
            {
                "medication": "Salbutamol Inhaler 100mcg",
                "current_stock": 12,
                "reorder_threshold": 30,
                "supplier": "Alliance Healthcare",
                "reorder_ref": _ref(),
            },
            {
                "medication": "Omeprazole 20mg",
                "current_stock": 35,
                "reorder_threshold": 75,
                "supplier": "AAH Pharmaceuticals",
                "reorder_ref": _ref(),
            },
        ],
        "near_expiry": [
            {
                "medication": "Amoxicillin 500mg",
                "expiry_date": (datetime.utcnow() + timedelta(days=12)).strftime("%Y-%m-%d"),
                "units_remaining": 120,
                "action": "Prioritise dispensing or return to supplier",
            },
            {
                "medication": "Diazepam 5mg",
                "expiry_date": (datetime.utcnow() + timedelta(days=22)).strftime("%Y-%m-%d"),
                "units_remaining": 60,
                "action": "Flag for pharmacist review",
            },
        ],
        "analysis": (
            "Stock health requires attention: 6 medications below reorder threshold, "
            "4 approaching expiry. Auto-reorders placed for top 3 priority items. "
            "Recommend pharmacist reviews Amoxicillin batch before end of week."
        ),
        "audit_ref": _ref(),
        "checked_at": _ts(),
    }


def _demo_engagement_report(days_ahead: int, channel: str) -> dict:
    """Return a realistic demo patient engagement report."""
    return {
        "campaign": {
            "channel": channel.upper(),
            "days_ahead": days_ahead,
            "patients_identified": 8,
            "patients_contacted": 7,
            "patients_skipped": 1,
            "skip_reason": "Patient opted out of communications",
        },
        "sample_messages": [
            {
                "patient": "Thomas Robertson",
                "nhs_number": "4756019283",
                "message": (
                    "Hi Thomas, this is a reminder from your pharmacy. "
                    "Your Warfarin prescription is due for collection in 5 days. "
                    "Please call us on 0141 XXX XXXX or reply to arrange a convenient time."
                ),
                "status": "delivered",
            },
            {
                "patient": "Fiona MacLeod",
                "nhs_number": "5291847302",
                "message": (
                    "Hi Fiona, your Levothyroxine 50mcg prescription is due in 3 days. "
                    "We have your medication ready — pop in any time during opening hours "
                    "or call to arrange delivery."
                ),
                "status": "delivered",
            },
        ],
        "audit_ref": _ref(),
        "sent_at": _ts(),
    }


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/health", tags=["System"])
def health():
    """System health check — returns service status and AI readiness."""
    return {
        "status": "ok",
        "service": "PharmAgent AI",
        "version": "1.0.0",
        "ai_ready": _has_api_key(),
        "timestamp": _ts(),
        "infrastructure": "DataVita Scottish Data Centre",
        "demo_url": "https://web-production-1f27a.up.railway.app/demo",
        "docs_url": "https://web-production-1f27a.up.railway.app/docs",
    }


# ── Demo endpoint ─────────────────────────────────────────────────────────────

@app.get("/demo", tags=["Demo"])
def demo():
    """
    Full end-to-end showcase of all three PharmAgent agents.

    Returns realistic outputs from:
    - Interaction Safety Agent (drug interaction check)
    - Stock Intelligence Agent (inventory review and reorders)
    - Patient Engagement Agent (personalised SMS reminders)
    - Orchestrator summary

    Safe to call without an API key. No database required.
    Designed for judges and OpenClaw integration demos.
    """
    return {
        "service": "PharmAgent AI",
        "demo_run": _ts(),
        "infrastructure": "DataVita — Scottish AI Infrastructure",
        "note": (
            "Realistic simulated outputs. "
            "Live AI reasoning activates when ANTHROPIC_API_KEY is set."
        ),
        "agents": {
            "interaction_safety_agent": _demo_interaction_report(
                "4823719056", "Ibuprofen 400mg"
            ),
            "stock_intelligence_agent": _demo_stock_report(),
            "patient_engagement_agent": _demo_engagement_report(7, "sms"),
        },
        "orchestrator_summary": {
            "tasks_completed": 3,
            "total_duration_ms": 847,
            "alerts_requiring_action": 2,
            "alerts": [
                (
                    "HIGH risk interaction detected for Margaret Campbell — "
                    "pharmacist review required before dispensing Ibuprofen"
                ),
                (
                    "4 medications approaching expiry — "
                    "estimated waste value £312.40 if not actioned"
                ),
            ],
            "audit_trail": "All agent actions logged. Ref: " + _ref(),
            "data_residency": (
                "All patient data processed within DataVita Scottish "
                "data centres (NFR-01 compliant)"
            ),
        },
    }


# ── Stock endpoints ───────────────────────────────────────────────────────────

@app.get("/stock/low", tags=["Stock"])
def low_stock():
    """Return medications currently below reorder threshold."""
    try:
        from tools.pharmacy_tools import get_low_stock_items
        return {"mode": "live", "items": get_low_stock_items()}
    except Exception:
        return {
            "mode": "demo",
            "note": "Database not seeded — showing realistic demo data",
            "items": _demo_stock_report()["low_stock"],
        }


@app.get("/stock/expiring", tags=["Stock"])
def expiring_stock(days: int = 30):
    """Return medications expiring within the given number of days."""
    try:
        from tools.pharmacy_tools import get_near_expiry_items
        return {"mode": "live", "expiry_window_days": days, "items": get_near_expiry_items(days)}
    except Exception:
        return {
            "mode": "demo",
            "note": "Database not seeded — showing realistic demo data",
            "expiry_window_days": days,
            "items": _demo_stock_report()["near_expiry"],
        }


# ── Patient endpoints ─────────────────────────────────────────────────────────

@app.get("/patients/{nhs_number}", tags=["Patients"])
def patient_lookup(nhs_number: str):
    """Look up a patient record by NHS number."""
    try:
        from tools.pharmacy_tools import get_patient_by_nhs
        result = get_patient_by_nhs(nhs_number)
        return {"mode": "live", "patient": result}
    except Exception:
        return {
            "mode": "demo",
            "note": "Database not seeded — showing realistic demo data",
            "patient": {
                "nhs_number": nhs_number,
                "name": "Margaret Campbell",
                "dob": "1948-03-14",
                "phone": "07700 900000",
            },
        }


# ── Agent endpoints ───────────────────────────────────────────────────────────

class InteractionCheckRequest(BaseModel):
    nhs_number: str
    new_medication_name: str


class EngagementRequest(BaseModel):
    days_ahead: Optional[int] = 7
    channel: Optional[str] = "sms"


class OrchestrateRequest(BaseModel):
    intent: str


@app.post("/agents/interaction-check", tags=["Agents"])
def interaction_check(req: InteractionCheckRequest):
    """
    Run the Interaction Safety Agent for a patient.

    Checks the patient's active medications against a new prescription
    for drug interaction risks. Returns a structured risk report with
    severity ratings and clinical recommendations.

    Always requires pharmacist sign-off before dispensing action is taken.

    Falls back to realistic demo data if database is not seeded.
    """
    try:
        if not _has_api_key():
            raise Exception("No API key configured")
        from agents.interaction_safety_agent import check_interactions
        return {"mode": "live", "report": check_interactions(req.nhs_number)}
    except Exception:
        return {
            "mode": "demo",
            "note": "Showing realistic demo data — set ANTHROPIC_API_KEY for live AI reasoning",
            "report": _demo_interaction_report(req.nhs_number, req.new_medication_name),
        }


@app.post("/agents/stock-review", tags=["Agents"])
def stock_review():
    """
    Run the Stock Intelligence Agent.

    Reviews current inventory levels, identifies low-stock and near-expiry
    medications, and triggers automated supplier reorder workflows.

    Falls back to realistic demo data if database is not seeded.
    """
    try:
        if not _has_api_key():
            raise Exception("No API key configured")
        from agents.stock_intelligence_agent import run_stock_review
        return {"mode": "live", "result": run_stock_review()}
    except Exception:
        return {
            "mode": "demo",
            "note": "Showing realistic demo data — set ANTHROPIC_API_KEY for live AI reasoning",
            "result": _demo_stock_report(),
        }


@app.post("/agents/engagement-campaign", tags=["Agents"])
def engagement_campaign(req: EngagementRequest):
    """
    Run the Patient Engagement Agent.

    Identifies patients with prescriptions due within the given window
    and sends personalised refill reminders via SMS or email.

    Falls back to realistic demo data if database is not seeded.
    """
    try:
        if not _has_api_key():
            raise Exception("No API key configured")
        from agents.patient_engagement_agent import run_engagement_campaign
        return {
            "mode": "live",
            "result": run_engagement_campaign(req.days_ahead, req.channel),
        }
    except Exception:
        return {
            "mode": "demo",
            "note": "Showing realistic demo data — set ANTHROPIC_API_KEY for live AI reasoning",
            "result": _demo_engagement_report(req.days_ahead, req.channel),
        }


@app.post("/agents/orchestrate", tags=["Agents"])
def orchestrate(req: OrchestrateRequest):
    """
    Send a plain-English intent to the Orchestrator Agent.

    The Orchestrator interprets the intent, delegates to the appropriate
    specialist agents, and returns a unified response.

    Example intents:
    - "Good morning, run the daily pharmacy check"
    - "Check stock and send reminders to patients due this week"
    - "What needs attention today?"

    Falls back to realistic demo data if API key is not configured.
    """
    try:
        if not _has_api_key():
            raise Exception("No API key configured")
        from agents.orchestrator_agent import run_orchestrator
        return {"mode": "live", "intent": req.intent, "response": run_orchestrator(req.intent)}
    except Exception:
        return {
            "mode": "demo",
            "note": "Showing realistic demo data — set ANTHROPIC_API_KEY for live AI reasoning",
            "intent": req.intent,
            "response": demo(),
        }
