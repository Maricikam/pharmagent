"""
api/main.py — PharmAgent AI FastAPI application.
"""

import os
import random
import string
from datetime import datetime, timedelta
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(
    title="PharmAgent AI",
    description=(
        "Intelligent Agent System for Pharmacy Management. "
        "Built for the DataVita OpenClaw Challenge. "
        "PharmAgent AI integrates multiple specialized agents to assist pharmacists with medication safety, stock management, and patient engagement. "
        "**Quick links:** [/demo](/demo) · [/health](/health) · [GitHub](https://github.com/Maricikam/pharmagent)"
    ),
    version="1.0.0",
)

app.mount("/static", StaticFiles(directory="api/static"), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _ref() -> str:
    return "REF-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=8))


def _ts() -> str:
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def _has_api_key() -> bool:
    return bool(os.getenv("ANTHROPIC_API_KEY", "").strip())


@app.get("/health", tags=["System"])
def health():
    return {
        "status": "ok",
        "service": "PharmAgent AI",
        "version": "1.0.0",
        "ai_ready": _has_api_key(),
        "timestamp": _ts(),
        "infrastructure": "DataVita Scottish Data Centre",
    }


@app.get("/demo", tags=["Demo"])
def demo():
    return {
        "service": "PharmAgent AI",
        "demo_run": _ts(),
        "infrastructure": "DataVita — Scottish AI Infrastructure",
        "note": "Realistic simulated outputs. Live AI mode activates when ANTHROPIC_API_KEY is set.",
        "agents": {
            "interaction_safety_agent": {
                "patient": {"name": "Margaret Campbell", "nhs_number": "4823719056", "dob": "1948-03-14"},
                "active_medications": [
                    {"name": "Warfarin", "dose": "5mg", "frequency": "Once daily"},
                    {"name": "Aspirin", "dose": "75mg", "frequency": "Once daily"},
                    {"name": "Atorvastatin", "dose": "40mg", "frequency": "Once nightly"},
                ],
                "new_medication_name": "Ibuprofen 400mg",
                "interaction_report": {
                    "risk_level": "HIGH",
                    "interactions_detected": [
                        {
                            "drug_a": "Warfarin", "drug_b": "Ibuprofen", "severity": "Major",
                            "mechanism": "NSAIDs inhibit platelet aggregation and may displace warfarin from plasma protein binding, significantly increasing bleeding risk.",
                            "recommendation": "DO NOT DISPENSE without prescriber review. Consider paracetamol as a safer alternative.",
                        },
                        {
                            "drug_a": "Aspirin", "drug_b": "Ibuprofen", "severity": "Moderate",
                            "mechanism": "Concurrent NSAID use increases GI bleeding risk.",
                            "recommendation": "Avoid combination if possible.",
                        },
                    ],
                    "clinical_decision": "REQUIRES PHARMACIST REVIEW — do not dispense without consultation",
                    "audit_ref": _ref(), "checked_at": _ts(),
                },
            },
            "stock_intelligence_agent": {
                "low_stock": [
                    {"medication": "Metformin 500mg", "current_stock": 48, "reorder_threshold": 100},
                    {"medication": "Salbutamol Inhaler", "current_stock": 12, "reorder_threshold": 30},
                ],
                "near_expiry": [
                    {"medication": "Amoxicillin 500mg", "expiry_date": (datetime.utcnow() + timedelta(days=12)).strftime("%Y-%m-%d"), "units": 120},
                ],
            },
            "patient_engagement_agent": {
                "campaign": {"channel": "SMS", "patients_contacted": 7},
                "sample_messages": [
                    {"patient": "Thomas Robertson", "message": "Hi Thomas, your Warfarin prescription is due in 5 days. Please contact your pharmacy to arrange collection."},
                ],
            },
        },
    }


@app.get("/patients/{nhs_number}", tags=["Patients"])
def patient_lookup(nhs_number: str):
    try:
        from tools.pharmacy_tools import get_patient_by_nhs, get_active_prescriptions
        patient = get_patient_by_nhs(nhs_number)
        if "error" in patient:
            raise HTTPException(status_code=404, detail=patient["error"])
        prescriptions = get_active_prescriptions(patient["id"])
        return {
            "patient": {
                "name": patient["name"],
                "nhs_number": nhs_number,
                "dob": patient["date_of_birth"],
                "active_medications": [
                    {"name": p["medication"], "dose": p["dosage"], "frequency": p["frequency"]}
                    for p in prescriptions
                ],
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stock/low", tags=["Stock"])
def low_stock():
    try:
        from tools.pharmacy_tools import get_low_stock_items
        items = get_low_stock_items()
        return {"low_stock": items}
    except Exception:
        return {
            "low_stock": [
                {"name": "Metformin 500mg", "current_stock": 48, "reorder_threshold": 100},
                {"name": "Salbutamol Inhaler", "current_stock": 12, "reorder_threshold": 30},
            ]
        }


@app.get("/stock/expiring", tags=["Stock"])
def expiring_stock(days: int = 30):
    try:
        from tools.pharmacy_tools import get_expiring_stock
        items = get_expiring_stock(days)
        return {"expiring_stock": items}
    except Exception:
        return {
            "expiring_stock": [
                {"name": "Amoxicillin 500mg", "expiry_date": (datetime.utcnow() + timedelta(days=12)).strftime("%Y-%m-%d")},
            ]
        }



class InteractionCheckRequest(BaseModel):
    nhs_number: str
    new_medication_name: str


class EngagementRequest(BaseModel):
    campaign_type: Optional[str] = "refill_reminder"


class OrchestrateRequest(BaseModel):
    intent: str

class ReorderRequest(BaseModel):
    medication_name: str
    quantity: int
    supplier: str

@app.post("/stock/reorder", tags=["Stock"])
def reorder_stock(req: ReorderRequest):
    try:
        from tools.pharmacy_tools import place_reorder
        result = place_reorder(
            medication_name=req.medication_name,
            quantity=req.quantity,
            supplier=req.supplier,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/agents/interaction-check", tags=["Agents"])
def interaction_check(req: InteractionCheckRequest):
    """Run the Interaction Safety Agent for a patient."""
    if not _has_api_key():
        return {"mode": "demo", "report": demo()["agents"]["interaction_safety_agent"]}
    try:
        from tools.pharmacy_tools import get_patient_by_nhs, get_active_prescriptions
        from agents.interaction_safety_agent import check_interactions
        patient = get_patient_by_nhs(req.nhs_number)
        if "error" in patient:
            raise HTTPException(status_code=404, detail=patient["error"])
        prescriptions = get_active_prescriptions(patient["id"])
        result = check_interactions(req.nhs_number, req.new_medication_name)
        return {
            "mode": "live",
            "report": {
                "patient": {
                    "name": patient["name"],
                    "nhs_number": req.nhs_number,
                    "dob": patient["date_of_birth"],
                },
                "active_medications": [
                    {"name": p["medication"], "dose": p["dosage"], "frequency": p["frequency"]}
                    for p in prescriptions
                ],
                "new_medication": req.new_medication_name,
                "interaction_report": {
                    "risk_level": "HIGH" if "CRITICAL" in result or "DO NOT" in result else "MODERATE" if "REVIEW" in result else "LOW",
                    "interactions_detected": [],
                    "clinical_decision": result,
                    "audit_ref": _ref(),
                    "checked_at": _ts(),
                },
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/agents/stock-review", tags=["Agents"])
def stock_review():
    """Run the Stock Intelligence Agent."""
    if not _has_api_key():
        return {"mode": "demo", "result": demo()["agents"]["stock_intelligence_agent"]}
    try:
        from agents.stock_intelligence_agent import run_stock_review
        return {"mode": "live", "result": run_stock_review()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/agents/engagement-campaign", tags=["Agents"])
def engagement_campaign(req: EngagementRequest):
    if not _has_api_key():
        return {"mode": "demo", "result": demo()["agents"]["patient_engagement_agent"]}
    try:
        from agents.patient_engagement_agent import run_engagement_campaign
        result = run_engagement_campaign(days_ahead=7, channel="sms", campaign_type=req.campaign_type)
        return {"mode": "live", "message": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/agents/orchestrate", tags=["Agents"])
def orchestrate(req: OrchestrateRequest):
    """Send a plain-English intent to the Orchestrator Agent."""
    if not _has_api_key():
        return {"mode": "demo", "intent": req.intent, "demo_output": demo()}
    try:
        from agents.orchestrator_agent import run_orchestrator
        return {"mode": "live", "response": run_orchestrator(req.intent)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
