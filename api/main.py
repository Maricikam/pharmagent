"""
api/main.py — PharmAgent AI FastAPI application.
"""

import os
import re
import random
import string
from datetime import datetime, timedelta
from typing import Optional

from fastapi import FastAPI, HTTPException, Depends, Security, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security.api_key import APIKeyHeader
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, field_validator
from dotenv import load_dotenv
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

load_dotenv()

limiter = Limiter(key_func=get_remote_address)

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

app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")), name="static")


@app.on_event("startup")
def startup():
    from db.database import init_db
    from tools.pharmacy_tools import get_patient_by_nhs
    from scripts.seed import refresh_due_dates
    init_db()
    if "error" in get_patient_by_nhs("1203480016"):
        from scripts.seed import seed
        seed()
    else:
        refresh_due_dates()


app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # open for demo; restrict to your domain in production
    allow_methods=["*"],
    allow_headers=["*"],
)


_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def require_api_key(api_key: str = Security(_api_key_header)):
    expected = os.getenv("API_KEY", "").strip()
    if expected and api_key != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing API key. Provide it via the X-API-Key header.")


def _ref() -> str:
    return "REF-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=8))


def _ts() -> str:
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def _local_ts() -> str:
    """Return current time in Europe/London (BST/GMT) as a readable string."""
    try:
        from zoneinfo import ZoneInfo
        now = datetime.now(ZoneInfo("Europe/London"))
    except Exception:
        now = datetime.utcnow() + timedelta(hours=1)
    return now.strftime("%d/%m/%Y  %H:%M")


def _has_api_key() -> bool:
    return bool(os.getenv("ANTHROPIC_API_KEY", "").strip())


def _parse_risk_level(text: str) -> str:
    t = text.upper()
    if "DO NOT DISPENSE" in t or re.search(r"\|\s*HIGH\s*\|", t):
        return "HIGH"
    if re.search(r"\|\s*MODERATE\s*\|", t) or "PHARMACIST REVIEW" in t:
        return "MODERATE"
    if "SAFE TO DISPENSE" in t:
        return "LOW"
    return "MODERATE"


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
                "patient": {"name": "Margaret Campbell", "nhs_number": "1203480016", "dob": "1948-03-12"},
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


@app.get("/patients/{nhs_number}", tags=["Patients"], dependencies=[Depends(require_api_key)])
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


@app.get("/stock/low", tags=["Stock"], dependencies=[Depends(require_api_key)])
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


@app.get("/stock/expiring", tags=["Stock"], dependencies=[Depends(require_api_key)])
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



def _validate_chi(chi: str) -> str:
    """Validate a Scottish CHI number: 10 digits, DDMMYY date prefix, Modulus 11 check digit."""
    chi = chi.strip()
    if not chi.isdigit() or len(chi) != 10:
        raise ValueError("CHI number must be exactly 10 digits.")
    dd, mm, yy = int(chi[0:2]), int(chi[2:4]), int(chi[4:6])
    if not (1 <= dd <= 31 and 1 <= mm <= 12):
        raise ValueError("CHI number must begin with a valid date (DDMMYY).")
    weights = [10, 9, 8, 7, 6, 5, 4, 3, 2]
    total = sum(int(chi[i]) * weights[i] for i in range(9))
    remainder = total % 11
    check = 0 if remainder == 0 else 11 - remainder
    if check == 10:
        raise ValueError("Invalid CHI number (check digit cannot be 10).")
    if int(chi[9]) != check:
        raise ValueError("Invalid CHI number (check digit mismatch).")
    return chi


class InteractionCheckRequest(BaseModel):
    nhs_number: str
    new_medication_name: str

    @field_validator("nhs_number")
    @classmethod
    def validate_chi(cls, v: str) -> str:
        try:
            return _validate_chi(v)
        except ValueError as e:
            raise ValueError(str(e)) from e


class EngagementRequest(BaseModel):
    campaign_type: Optional[str] = "refill_reminder"


class OrchestrateRequest(BaseModel):
    intent: str

class ReorderRequest(BaseModel):
    medication_name: str
    quantity: int
    supplier: str

class DisposeRequest(BaseModel):
    medication_name: str
    action: str  # "dispose" or "return"
    quantity: int
    expiry_date: str

@app.post("/stock/reorder", tags=["Stock"], dependencies=[Depends(require_api_key)])
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

@app.post("/stock/dispose", tags=["Stock"], dependencies=[Depends(require_api_key)])
def dispose_stock_endpoint(req: DisposeRequest):
    try:
        from tools.pharmacy_tools import dispose_stock
        result = dispose_stock(
            medication_name=req.medication_name,
            action=req.action,
            quantity=req.quantity,
            expiry_date=req.expiry_date,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/agents/interaction-check", tags=["Agents"], dependencies=[Depends(require_api_key)])
@limiter.limit("30/minute")
def interaction_check_get(request: Request, nhs_number: str, new_medication_name: str):
    """GET version for OpenClaw/web-fetch compatibility."""
    try:
        req = InteractionCheckRequest(nhs_number=nhs_number, new_medication_name=new_medication_name)
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))
    return interaction_check(request, req)


@app.post("/agents/interaction-check", tags=["Agents"], dependencies=[Depends(require_api_key)])
@limiter.limit("30/minute")
def interaction_check(request: Request, req: InteractionCheckRequest):
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
        result = check_interactions(req.nhs_number, req.new_medication_name,
                                    _patient=patient, _prescriptions=prescriptions)
        return {
            "mode": "live",
            "report": {
                "patient": {
                    "name": patient["name"],
                    "nhs_number": req.nhs_number,
                    "dob": patient["date_of_birth"],
                    "age": result.get("age"),
                },
                "active_medications": [
                    {"name": p["medication"], "dose": p["dosage"], "frequency": p["frequency"]}
                    for p in prescriptions
                ],
                "new_medication": req.new_medication_name,
                "interaction_report": {
                    "risk_level": result["risk_level"],
                    "interactions_detected": result["interactions_detected"],
                    "clinical_decision": result["text"],
                    "audit_ref": _ref(),
                    "checked_at": _ts(),
                },
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/agents/stock-review", tags=["Agents"], dependencies=[Depends(require_api_key)])
@limiter.limit("30/minute")
def stock_review_get(request: Request):
    """GET version for OpenClaw/web-fetch compatibility."""
    return stock_review(request)


@app.post("/agents/stock-review", tags=["Agents"], dependencies=[Depends(require_api_key)])
@limiter.limit("30/minute")
def stock_review(request: Request):
    """Run the Stock Intelligence Agent."""
    if not _has_api_key():
        return {"mode": "demo", "result": demo()["agents"]["stock_intelligence_agent"]}
    try:
        from agents.stock_intelligence_agent import run_stock_review
        return {"mode": "live", "result": run_stock_review()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/agents/engagement-campaign", tags=["Agents"], dependencies=[Depends(require_api_key)])
@limiter.limit("30/minute")
def engagement_campaign_get(request: Request, campaign_type: str = "refill_reminder"):
    """GET version for OpenClaw/web-fetch compatibility."""
    req = EngagementRequest(campaign_type=campaign_type)
    return engagement_campaign(request, req)


@app.post("/agents/engagement-campaign", tags=["Agents"], dependencies=[Depends(require_api_key)])
@limiter.limit("30/minute")
def engagement_campaign(request: Request, req: EngagementRequest):
    if not _has_api_key():
        return {"mode": "demo", "result": demo()["agents"]["patient_engagement_agent"]}
    try:
        from agents.patient_engagement_agent import run_engagement_campaign
        result = run_engagement_campaign(days_ahead=7, channel="sms", campaign_type=req.campaign_type)
        return {"mode": "live", "message": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/audit/logs", tags=["Audit"], dependencies=[Depends(require_api_key)])
def audit_logs(limit: int = 50):
    """Return the most recent audit log entries."""
    try:
        from tools.pharmacy_tools import get_recent_audit_logs
        return {"logs": get_recent_audit_logs(limit=limit)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/agents/patient-profile", tags=["Agents"], dependencies=[Depends(require_api_key)])
def patient_profile(nhs_number: str = None, name: str = None):
    """Look up a patient's full medication profile by CHI number or name."""
    try:
        from tools.pharmacy_tools import get_patient_by_nhs, get_patient_by_name, get_active_prescriptions
        if not nhs_number and not name:
            raise HTTPException(status_code=422, detail="Provide nhs_number or name.")
        if name and not nhs_number:
            matches = get_patient_by_name(name)
            if not matches:
                raise HTTPException(status_code=404, detail=f"No patient found matching '{name}'.")
            if len(matches) > 1:
                return {"multiple_matches": matches}
            nhs_number = matches[0]["nhs_number"]
        patient = get_patient_by_nhs(nhs_number)
        if "error" in patient:
            raise HTTPException(status_code=404, detail=patient["error"])
        prescriptions = get_active_prescriptions(patient["id"])
        return {
            "patient": patient,
            "active_prescriptions": prescriptions,
            "prescription_count": len(prescriptions),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/agents/handover", tags=["Agents"], dependencies=[Depends(require_api_key)])
@limiter.limit("10/minute")
def handover(request: Request):
    """Generate a shift handover briefing for the incoming pharmacist."""
    if not _has_api_key():
        return {"mode": "demo", "note": "Handover agent requires a live API key."}
    try:
        from agents.handover_agent import generate_handover
        return {"mode": "live", "result": generate_handover()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class EmergencySupplyRequest(BaseModel):
    medication: str
    quantity: int
    reason: str
    nhs_number: Optional[str] = None
    patient_name: Optional[str] = None
    prescriber_contacted: bool = False

    @field_validator("nhs_number")
    @classmethod
    def validate_chi(cls, v):
        if v is None:
            return v
        try:
            return _validate_chi(v)
        except ValueError as e:
            raise ValueError(str(e)) from e


@app.post("/agents/emergency-supply", tags=["Agents"], dependencies=[Depends(require_api_key)])
@limiter.limit("20/minute")
def emergency_supply(request: Request, req: EmergencySupplyRequest):
    """Generate an emergency supply record with interaction check and audit log."""
    if not _has_api_key():
        return {"mode": "demo", "note": "Emergency supply agent requires a live API key."}
    if not req.nhs_number and not req.patient_name:
        raise HTTPException(status_code=422, detail="Provide nhs_number or patient_name.")
    try:
        from agents.emergency_supply_agent import process_emergency_supply
        result = process_emergency_supply(
            medication=req.medication,
            quantity=req.quantity,
            reason=req.reason,
            nhs_number=req.nhs_number,
            patient_name=req.patient_name,
            prescriber_contacted=req.prescriber_contacted,
        )
        if "error" in result:
            status = 409 if result["error"] == "multiple_patients" else 404
            raise HTTPException(status_code=status, detail=result)
        return {"mode": "live", "result": result}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/agents/emergency-supply", tags=["Agents"], dependencies=[Depends(require_api_key)])
@limiter.limit("20/minute")
def emergency_supply_get(request: Request, medication: str, quantity: int, reason: str,
                          nhs_number: str = None, patient_name: str = None,
                          prescriber_contacted: bool = False):
    """GET version for OpenClaw compatibility."""
    req = EmergencySupplyRequest(
        medication=medication, quantity=quantity, reason=reason,
        nhs_number=nhs_number, patient_name=patient_name,
        prescriber_contacted=prescriber_contacted,
    )
    return emergency_supply(request, req)


@app.get("/agents/analytics/workload", tags=["Analytics"], dependencies=[Depends(require_api_key)])
def workload_preview(days: int = 7):
    """Prescriptions due per day for the next N days — no AI call needed."""
    try:
        from tools.pharmacy_tools import get_workload_preview
        data = get_workload_preview(days)
        total = sum(d["prescriptions_due"] for d in data)
        peak = max(data, key=lambda d: d["prescriptions_due"]) if data else None
        return {
            "days": days,
            "total_prescriptions_due": total,
            "peak_day": peak,
            "workload": data,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/agents/analytics/prioritize-patients", tags=["Analytics"], dependencies=[Depends(require_api_key)])
@limiter.limit("10/minute")
def api_prioritize_patients(request: Request):
    """Score and rank all patients by clinical urgency (overdue, adherence risk, polypharmacy)."""
    if not _has_api_key():
        return {"mode": "demo", "note": "Analytics agent requires a live API key."}
    try:
        from agents.analytics_agent import prioritize_patients
        return {"mode": "live", "result": prioritize_patients()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/agents/analytics/anomalies", tags=["Analytics"], dependencies=[Depends(require_api_key)])
@limiter.limit("10/minute")
def api_detect_anomalies(request: Request):
    """Detect unusual patterns across stock, prescriptions, and patient behaviour."""
    if not _has_api_key():
        return {"mode": "demo", "note": "Analytics agent requires a live API key."}
    try:
        from agents.analytics_agent import detect_anomalies
        return {"mode": "live", "result": detect_anomalies()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/agents/analytics/workflow", tags=["Analytics"], dependencies=[Depends(require_api_key)])
@limiter.limit("10/minute")
def api_workflow_optimization(request: Request):
    """AI-driven workflow optimization recommendations based on pharmacy state and audit history."""
    if not _has_api_key():
        return {"mode": "demo", "note": "Analytics agent requires a live API key."}
    try:
        from agents.analytics_agent import get_workflow_optimization
        return {"mode": "live", "result": get_workflow_optimization()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/agents/orchestrate", tags=["Agents"], dependencies=[Depends(require_api_key)])
@limiter.limit("30/minute")
def orchestrate(request: Request, req: OrchestrateRequest):
    """Send a plain-English intent to the Orchestrator Agent."""
    if not _has_api_key():
        return {"mode": "demo", "intent": req.intent, "demo_output": demo()}
    try:
        from agents.orchestrator_agent import run_orchestrator
        intent_with_time = f"[Current time: {_local_ts()} BST]\n{req.intent}"
        return {"mode": "live", "response": run_orchestrator(intent_with_time)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
