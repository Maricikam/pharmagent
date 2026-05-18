"""
api/main.py — PharmAgent AI FastAPI application.
Includes a /demo endpoint for judges and OpenClaw showcase.
"""

import os
import random
import string
from datetime import datetime, timedelta
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from fastapi.staticfiles import StaticFiles

app = FastAPI(
    title="PharmAgent AI",
    description=(
        "Intelligent Agent System for Pharmacy Management. "
        "Built for the DataVita OpenClaw Challenge. "
        "HND Software Development — New College Lanarkshire."
    ),
    version="1.0.0",
)

app.mount("/static", StaticFiles(directory="static"), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _ref() -> str:
    return "REF-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=8))


def _ts() -> str:
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def _has_api_key() -> bool:
    return bool(os.getenv("ANTHROPIC_API_KEY", "").strip())


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/health", tags=["System"])
def health():
    """System health check."""
    return {
        "status": "ok",
        "service": "PharmAgent AI",
        "version": "1.0.0",
        "ai_ready": _has_api_key(),
        "timestamp": _ts(),
        "infrastructure": "DataVita Scottish Data Centre",
    }


# ── Demo endpoint ─────────────────────────────────────────────────────────────

@app.get("/demo", tags=["Demo"])
def demo():
    """
    Full end-to-end demo of all three PharmAgent agents.
    Returns simulated outputs from each agent in a single response.
    Safe to call without an Anthropic API key — uses realistic mock data.
    Designed for judges and OpenClaw showcase.
    """
    return {
        "service": "PharmAgent AI",
        "demo_run": _ts(),
        "infrastructure": "DataVita — Scottish AI Infrastructure",
        "note": "Realistic simulated outputs. Live AI mode activates when ANTHROPIC_API_KEY is set.",

        "agents": {

            "interaction_safety_agent": {
                "patient": {
                    "name": "Margaret Campbell",
                    "nhs_number": "4823719056",
                    "dob": "1948-03-14",
                },
                "active_medications": [
                    {"name": "Warfarin", "dose": "5mg", "frequency": "Once daily"},
                    {"name": "Aspirin", "dose": "75mg", "frequency": "Once daily"},
                    {"name": "Atorvastatin", "dose": "40mg", "frequency": "Once nightly"},
                ],
                "new_medication": "Ibuprofen 400mg",
                "interaction_report": {
                    "risk_level": "HIGH",
                    "interactions_detected": [
                        {
                            "drug_a": "Warfarin",
                            "drug_b": "Ibuprofen",
                            "severity": "Major",
                            "mechanism": "NSAIDs inhibit platelet aggregation and may displace warfarin from plasma protein binding, significantly increasing bleeding risk.",
                            "recommendation": "DO NOT DISPENSE without prescriber review. Consider paracetamol as a safer alternative.",
                        },
                        {
                            "drug_a": "Aspirin",
                            "drug_b": "Ibuprofen",
                            "severity": "Moderate",
                            "mechanism": "Concurrent NSAID use increases GI bleeding risk.",
                            "recommendation": "Avoid combination if possible.",
                        },
                    ],
                    "clinical_decision": "REQUIRES PHARMACIST REVIEW — do not dispense without consultation",
                    "audit_ref": _ref(),
                    "checked_at": _ts(),
                },
            },

            "stock_intelligence_agent": {
                "inventory_summary": {
                    "total_medications_tracked": 847,
                    "low_stock_items": 6,
                    "near_expiry_items": 4,
                    "reorders_triggered": 3,
                    "estimated_waste_value": "£312.40",
                },
                "low_stock": [
                    {"medication": "Metformin 500mg", "current_stock": 48, "reorder_threshold": 100, "supplier": "AAH Pharmaceuticals", "reorder_ref": _ref()},
                    {"medication": "Salbutamol Inhaler 100mcg", "current_stock": 12, "reorder_threshold": 30, "supplier": "Alliance Healthcare", "reorder_ref": _ref()},
                    {"medication": "Omeprazole 20mg", "current_stock": 35, "reorder_threshold": 75, "supplier": "AAH Pharmaceuticals", "reorder_ref": _ref()},
                ],
                "near_expiry": [
                    {"medication": "Amoxicillin 500mg", "expiry_date": (datetime.utcnow() + timedelta(days=12)).strftime("%Y-%m-%d"), "units_remaining": 120, "action": "Prioritise dispensing or return to supplier"},
                    {"medication": "Diazepam 5mg", "expiry_date": (datetime.utcnow() + timedelta(days=22)).strftime("%Y-%m-%d"), "units_remaining": 60, "action": "Flag for pharmacist review"},
                ],
                "analysis": "Stock health requires attention: 6 medications below reorder threshold, 4 approaching expiry. Auto-reorders placed for top 3 priority items. Recommend pharmacist reviews Amoxicillin batch before end of week.",
                "audit_ref": _ref(),
                "checked_at": _ts(),
            },

            "patient_engagement_agent": {
                "campaign": {
                    "channel": "SMS",
                    "days_ahead": 7,
                    "patients_identified": 8,
                    "patients_contacted": 7,
                    "patients_skipped": 1,
                    "skip_reason": "Patient opted out of communications",
                },
                "sample_messages": [
                    {
                        "patient": "Thomas Robertson",
                        "nhs_number": "4756019283",
                        "message": "Hi Thomas, this is a reminder from your pharmacy. Your Warfarin prescription is due for collection in 5 days. Please call us on 0141 XXX XXXX or reply to this message to arrange a convenient time.",
                        "status": "delivered",
                    },
                    {
                        "patient": "Fiona MacLeod",
                        "nhs_number": "5291847302",
                        "message": "Hi Fiona, your Levothyroxine 50mcg prescription is due in 3 days. We have your medication ready — pop in any time during opening hours or call to arrange delivery.",
                        "status": "delivered",
                    },
                ],
                "audit_ref": _ref(),
                "sent_at": _ts(),
            },
        },

        "orchestrator_summary": {
            "tasks_completed": 3,
            "total_duration_ms": 847,
            "alerts_requiring_action": 2,
            "alerts": [
                "HIGH risk interaction detected for Margaret Campbell — pharmacist review required before dispensing Ibuprofen",
                "4 medications approaching expiry — estimated waste value £312.40 if not actioned",
            ],
            "audit_trail": "All agent actions logged with full audit trail. Ref: " + _ref(),
            "data_residency": "All patient data processed within DataVita Scottish data centres (NFR-01 compliant)",
        },
    }


# ── Patient endpoints ─────────────────────────────────────────────────────────

@app.get("/patients/{nhs_number}", tags=["Patients"])
def patient_lookup(nhs_number: str):
    """Look up a patient by NHS number."""
    # Demo response — live version queries PostgreSQL
    return {
        "nhs_number": nhs_number,
        "name": "Demo Patient",
        "dob": "1960-01-01",
        "note": "Live patient data available when connected to DataVita-hosted PostgreSQL.",
    }


# ── Stock endpoints ───────────────────────────────────────────────────────────

@app.get("/stock/low", tags=["Stock"])
def low_stock():
    """Return medications below reorder threshold."""
    return {
        "low_stock_items": [
            {"medication": "Metformin 500mg", "current_stock": 48, "threshold": 100},
            {"medication": "Salbutamol Inhaler", "current_stock": 12, "threshold": 30},
        ],
        "note": "Live data from PostgreSQL inventory when deployed.",
    }


@app.get("/stock/expiring", tags=["Stock"])
def expiring_stock(days: int = 30):
    """Return medications expiring within the given window."""
    return {
        "expiry_window_days": days,
        "near_expiry_items": [
            {"medication": "Amoxicillin 500mg", "expiry_date": (datetime.utcnow() + timedelta(days=12)).strftime("%Y-%m-%d"), "units": 120},
        ],
        "note": "Live data from PostgreSQL inventory when deployed.",
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
    """Run the Interaction Safety Agent for a patient."""
    if not _has_api_key():
        return {
            "mode": "demo",
            "nhs_number": req.nhs_number,
            "new_medication": req.new_medication_name,
            "result": "Set ANTHROPIC_API_KEY to enable live AI interaction checking.",
            "demo_report": demo()["agents"]["interaction_safety_agent"],
        }
    # Live mode — import and run the actual agent
    try:
        from agents.interaction_safety_agent import check_interactions
        return {"mode": "live", "report": check_interactions(req.nhs_number)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/agents/stock-review", tags=["Agents"])
def stock_review():
    """Run the Stock Intelligence Agent."""
    if not _has_api_key():
        return {
            "mode": "demo",
            "result": demo()["agents"]["stock_intelligence_agent"],
        }
    try:
        from agents.stock_intelligence_agent import run_stock_review
        return {"mode": "live", "result": run_stock_review()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/agents/engagement-campaign", tags=["Agents"])
def engagement_campaign(req: EngagementRequest):
    """Run the Patient Engagement Agent."""
    if not _has_api_key():
        return {
            "mode": "demo",
            "days_ahead": req.days_ahead,
            "channel": req.channel,
            "result": demo()["agents"]["patient_engagement_agent"],
        }
    try:
        from agents.patient_engagement_agent import run_engagement_campaign
        return {"mode": "live", "result": run_engagement_campaign(req.days_ahead, req.channel)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/agents/orchestrate", tags=["Agents"])
def orchestrate(req: OrchestrateRequest):
    """Send a plain-English intent to the Orchestrator Agent."""
    if not _has_api_key():
        return {
            "mode": "demo",
            "intent": req.intent,
            "response": "Orchestrator running in demo mode. Set ANTHROPIC_API_KEY for live AI reasoning.",
            "demo_output": demo(),
        }
    try:
        from agents.orchestrator_agent import run_orchestrator
        return {"mode": "live", "response": run_orchestrator(req.intent)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
