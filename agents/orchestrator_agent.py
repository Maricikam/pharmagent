"""
Orchestrator Agent — PharmAgent AI
=====================================
Central coordinator that accepts plain-English intent from a pharmacist
and delegates to the appropriate specialist agents.

Responsibility:
    Receives a natural language request (e.g. "good morning, run the
    daily check"), interprets intent using Claude reasoning, decomposes
    the task into sub-tasks, delegates to specialist agents, and
    synthesises a unified response.

Sub-agents coordinated:
    - InteractionSafetyAgent  — drug interaction checking
    - StockIntelligenceAgent  — inventory management and reordering
    - PatientEngagementAgent  — refill reminder campaigns

Design pattern:
    Orchestrator pattern — single entry point for all pharmacy AI
    requests. Maintains separation of concerns by delegating domain
    logic entirely to specialist agents.

OpenClaw integration:
    This agent is the primary target of the pharmagent-daily-briefing
    and pharmagent-interaction-check OpenClaw skills. Natural language
    input from WhatsApp/Telegram is routed here via the FastAPI
    /agents/orchestrate endpoint.
"""

"""
Orchestrator Agent
The top-level coordinator. Takes a plain English request from a pharmacist
and decides which sub-agents to invoke, synthesises their outputs, and
returns a unified response.

This is the headline demo: one prompt → full multi-agent workflow.
"""
import anthropic
import json
from agents.interaction_safety_agent import check_interactions
from agents.stock_intelligence_agent import run_stock_review
from agents.patient_engagement_agent import run_engagement_campaign
from agents.handover_agent import generate_handover
from agents.emergency_supply_agent import process_emergency_supply
from agents.analytics_agent import prioritize_patients, detect_anomalies
from tools.pharmacy_tools import log_audit_event, get_patient_by_name, get_patient_by_nhs, get_active_prescriptions
from config import MODEL
MAX_TURNS = 5

client = anthropic.Anthropic()

TOOLS = [
    {
        "name": "lookup_patient",
        "description": (
            "Look up a patient by name when the pharmacist does not provide a CHI number. "
            "Returns matching patients with their CHI numbers. "
            "If multiple patients match, return the list so the pharmacist can clarify. "
            "Always call this before check_drug_interactions when only a name is given."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Patient name or partial name (e.g. 'Margaret Campbell' or 'Robertson')",
                }
            },
            "required": ["name"],
        },
    },
    {
        "name": "check_drug_interactions",
        "description": "Check a patient's active prescriptions for drug interaction risks. Use when a pharmacist asks about a specific patient's medications or safety.",
        "input_schema": {
            "type": "object",
            "properties": {
                "nhs_number": {
                    "type": "string",
                    "description": "The patient's 10-digit CHI number",
                },
                "new_medication": {
                    "type": "string",
                    "description": "Name of the new medication to check against the patient's current prescriptions (optional — omit to check all active medications for interactions)",
                },
            },
            "required": ["nhs_number"],
        },
    },
    {
        "name": "run_stock_review",
        "description": "Review pharmacy inventory: identify low stock items, expiring medications, and trigger reorders. Use for any stock, inventory, or supply chain requests.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "get_patient_profile",
        "description": "Get a patient's full medication profile. Use when asked what a patient is currently on, their prescription list, or their medication history. Requires either a CHI number or a patient name.",
        "input_schema": {
            "type": "object",
            "properties": {
                "nhs_number": {"type": "string", "description": "Patient's 10-digit CHI number (use if known)"},
                "name": {"type": "string", "description": "Patient name — will be resolved via lookup_patient if CHI not available"},
            },
            "required": [],
        },
    },
    {
        "name": "generate_handover",
        "description": "Generate a shift handover briefing for the incoming pharmacist. Use when asked for end-of-shift notes, handover, or a summary of what happened this shift.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "process_emergency_supply",
        "description": "Process an emergency medication supply request. Generates a legal NHS supply record with interaction check. Use when a patient has run out of medication and cannot reach their GP.",
        "input_schema": {
            "type": "object",
            "properties": {
                "medication": {"type": "string", "description": "Medication name and strength (e.g. 'Warfarin 5mg')"},
                "quantity": {"type": "integer", "description": "Number of units to supply"},
                "reason": {"type": "string", "description": "Reason for emergency supply"},
                "nhs_number": {"type": "string", "description": "Patient CHI number (optional if name provided)"},
                "patient_name": {"type": "string", "description": "Patient name (optional if CHI provided)"},
                "prescriber_contacted": {"type": "boolean", "description": "Whether the prescriber was contacted (default false)"},
            },
            "required": ["medication", "quantity", "reason"],
        },
    },
    {
        "name": "prioritize_patients",
        "description": (
            "Score and rank all patients by clinical urgency. Returns a sorted list with URGENT, HIGH, "
            "and ROUTINE priority levels based on overdue collections, adherence risk, and polypharmacy. "
            "Use when asked who needs attention today, patient prioritization, or who is most at risk."
        ),
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "detect_anomalies",
        "description": (
            "Detect unusual patterns across stock, prescriptions, and patient behaviour. "
            "Identifies overdue collections, polypharmacy risks, emergency supply spikes, "
            "and predicted stock shortages. Use when asked about anomalies, unusual patterns, "
            "or anything that needs investigating."
        ),
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "run_patient_engagement",
        "description": (
            "Contact patients with personalised messages. Supports multiple campaign types: "
            "refill_reminder (prescription due soon), adherence_check (missed collection), "
            "flu_vaccination (invite for NHS flu jab), spring_allergies (hay fever season), "
            "winter_wellness (cold/flu, vitamin D), travel_health (pre-trip medication advice), "
            "new_year_health (medicines review invitation), photosensitivity_summer (sun safety for at-risk meds), "
            "seasonal (general seasonal health check). Use when asked about patient outreach, reminders, "
            "vaccinations, seasonal campaigns, or any proactive patient communication."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "days_ahead": {
                    "type": "integer",
                    "description": "How many days ahead to look for due refills (default 7)",
                },
                "channel": {
                    "type": "string",
                    "enum": ["sms", "email"],
                    "description": "Communication channel to use",
                },
                "campaign_type": {
                    "type": "string",
                    "enum": [
                        "refill_reminder",
                        "adherence_check",
                        "seasonal",
                        "flu_vaccination",
                        "spring_allergies",
                        "winter_wellness",
                        "travel_health",
                        "new_year_health",
                        "photosensitivity_summer",
                    ],
                    "description": "Type of campaign to run (default: refill_reminder)",
                },
            },
            "required": [],
        },
    },
]

ORCHESTRATOR_SYSTEM = """You are the Orchestrator Agent for PharmAgent AI — a multi-agent pharmacy management system.

Your job is to:
1. Understand the pharmacist's request
2. Decide which specialist agents to call (you can call multiple)
3. Synthesise all results into a structured clinical report for the pharmacist

Available tools:
- lookup_patient: resolve a patient name to a CHI number — always use this first if no CHI is provided
- get_patient_profile: return a patient's full active medication list
- check_drug_interactions: patient-specific medication safety check (requires CHI number)
- run_stock_review: inventory management, low stock, expiry, predicted shortages, smart reorders
- run_patient_engagement: patient refill reminders and outreach campaigns
- generate_handover: shift handover note for the incoming pharmacist
- process_emergency_supply: emergency medication supply with legal record and interaction check
- prioritize_patients: rank all patients by urgency (URGENT/HIGH/ROUTINE) — overdue collections, adherence risk, polypharmacy
- detect_anomalies: find unusual patterns — overdue patients, shortage risks, emergency supply spikes, polypharmacy flags

If the pharmacist refers to a patient by name only, call lookup_patient first to get the CHI number, then proceed. If lookup returns multiple matches, list them and ask the pharmacist to clarify.

OUTPUT FORMAT — strictly follow this style:
- Write in a professional NHS clinical tone, as you would in a handover report or dispensing log
- Do NOT use emojis or decorative symbols of any kind
- Use plain section headers in title case, underlined with dashes (e.g. "Stock Review\n------------")
- Use dates in DD/MM/YYYY format and 24-hour time (e.g. 23/05/2026  16:04)
- Use plain numbered or bulleted lists with a hyphen (-) where appropriate
- Risk levels: write as "HIGH", "MODERATE", or "LOW" — no colour coding or icons
- For interaction alerts, use the label "INTERACTION ALERT — PHARMACIST ACTION REQUIRED" at the top
- End with a "Priority Actions" section listing items numbered by urgency: [URGENT], [TODAY], [THIS WEEK]
- Keep the overall report concise and scannable — no filler sentences or conversational padding"""


def run_orchestrator(pharmacist_request: str) -> str:
    print(f"\n🎯 Orchestrator received: '{pharmacist_request}'")
    print("─" * 60)

    messages = [{"role": "user", "content": pharmacist_request}]
    agent_results = {}

    response = client.messages.create(
        model=MODEL,
        max_tokens=1000,
        system=ORCHESTRATOR_SYSTEM,
        tools=TOOLS,
        messages=messages,
    )

    turns = 0
    while response.stop_reason == "tool_use" and turns < MAX_TURNS:
        turns += 1
        tool_results = []

        for block in response.content:
            if block.type != "tool_use":
                continue

            tool_name = block.name
            tool_input = block.input
            print(f"  🔧 Calling: {tool_name}({json.dumps(tool_input) if tool_input else ''})")

            if tool_name == "lookup_patient":
                matches = get_patient_by_name(tool_input["name"])
                if not matches:
                    result = f"No patients found matching '{tool_input['name']}'."
                elif len(matches) == 1:
                    p = matches[0]
                    result = f"Found: {p['name']} | CHI: {p['nhs_number']} | DOB: {p['date_of_birth']}"
                else:
                    lines = [f"Multiple patients found for '{tool_input['name']}':"]
                    for p in matches:
                        lines.append(f"  - {p['name']} | CHI: {p['nhs_number']} | DOB: {p['date_of_birth']}")
                    lines.append("Please ask the pharmacist to confirm which patient.")
                    result = "\n".join(lines)
                agent_results["patient_lookup"] = result

            elif tool_name == "check_drug_interactions":
                result = check_interactions(
                    tool_input["nhs_number"],
                    new_medication=tool_input.get("new_medication"),
                )
                agent_results["interaction_check"] = result
                result = result["text"] if isinstance(result, dict) else result

            elif tool_name == "get_patient_profile":
                nhs = tool_input.get("nhs_number")
                name = tool_input.get("name")
                if not nhs and name:
                    matches = get_patient_by_name(name)
                    if matches:
                        nhs = matches[0]["nhs_number"]
                if nhs:
                    patient = get_patient_by_nhs(nhs)
                    rxs = get_active_prescriptions(patient["id"]) if "error" not in patient else []
                    meds = ", ".join(f"{r['medication']} {r['dosage']}" for r in rxs) or "none"
                    result = (
                        f"Patient: {patient.get('name')} | CHI: {nhs} | DOB: {patient.get('date_of_birth')}\n"
                        f"Active medications ({len(rxs)}): {meds}"
                    )
                else:
                    result = "Could not resolve patient. Provide CHI number or full name."
                agent_results["patient_profile"] = result

            elif tool_name == "generate_handover":
                handover = generate_handover()
                result = handover["note"]
                agent_results["handover"] = result

            elif tool_name == "process_emergency_supply":
                supply = process_emergency_supply(
                    medication=tool_input["medication"],
                    quantity=tool_input["quantity"],
                    reason=tool_input["reason"],
                    nhs_number=tool_input.get("nhs_number"),
                    patient_name=tool_input.get("patient_name"),
                    prescriber_contacted=tool_input.get("prescriber_contacted", False),
                )
                if "error" in supply:
                    result = supply["message"]
                else:
                    result = supply["record"]
                agent_results["emergency_supply"] = result

            elif tool_name == "run_stock_review":
                stock = run_stock_review()
                result = stock["analysis"]
                if stock["orders_placed"]:
                    result += f"\n\nAuto-orders placed: {len(stock['orders_placed'])} reorders triggered."
                agent_results["stock_review"] = result

            elif tool_name == "prioritize_patients":
                prio = prioritize_patients()
                result = prio["report"]
                agent_results["patient_prioritization"] = result

            elif tool_name == "detect_anomalies":
                anomalies = detect_anomalies()
                result = anomalies["report"]
                agent_results["anomaly_detection"] = result

            elif tool_name == "run_patient_engagement":
                days = tool_input.get("days_ahead", 7)
                channel = tool_input.get("channel", "sms")
                campaign_type = tool_input.get("campaign_type", "refill_reminder")
                engagement = run_engagement_campaign(days_ahead=days, channel=channel, campaign_type=campaign_type)
                result = f"Contacted {engagement['patients_contacted']} patients via {channel}."
                if engagement["results"]:
                    result += "\nMessages sent:\n"
                    for r in engagement["results"]:
                        result += f"  - {r['patient']}: {r['message'][:80]}...\n"
                agent_results["engagement"] = result

            else:
                result = f"Unknown tool: {tool_name}"

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": str(result),
            })

        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user", "content": tool_results})

        response = client.messages.create(
            model=MODEL,
            max_tokens=1500,
            system=ORCHESTRATOR_SYSTEM,
            tools=TOOLS,
            messages=messages,
        )

    final_text = ""
    for block in response.content:
        if hasattr(block, "text"):
            final_text += block.text

    log_audit_event(
        agent="OrchestratorAgent",
        action="REQUEST_HANDLED",
        details=f"Request: '{pharmacist_request[:100]}' | Agents called: {list(agent_results.keys())}",
    )

    return final_text


if __name__ == "__main__":
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    print("=" * 60)
    print("  PharmAgent AI — Orchestrator Demo")
    print("=" * 60)

    print("\n[Demo 1] Full morning pharmacy check")
    result1 = run_orchestrator(
        "Good morning. Please do a full check: review our stock levels and "
        "send refill reminders to any patients due in the next 5 days."
    )
    print("\n📋 Orchestrator Summary:")
    print(result1)

    print("\n" + "=" * 60)

    print("\n[Demo 2] Patient-specific interaction check")
    result2 = run_orchestrator(
        "I need to check Margaret Campbell — CHI number 1203480016 — "
        "before I dispense her prescription. Any interaction concerns?"
    )
    print("\n📋 Orchestrator Summary:")
    print(result2)
