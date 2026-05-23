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
    This agent is the primary target of the pharmagent-morning-briefing
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
from tools.pharmacy_tools import log_audit_event

MODEL = "claude-haiku-4-5-20251001"
MAX_TURNS = 5

client = anthropic.Anthropic()

TOOLS = [
    {
        "name": "check_drug_interactions",
        "description": "Check a patient's active prescriptions for drug interaction risks. Use when a pharmacist asks about a specific patient's medications or safety.",
        "input_schema": {
            "type": "object",
            "properties": {
                "nhs_number": {
                    "type": "string",
                    "description": "The patient's 10-digit NHS number",
                }
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
        "name": "run_patient_engagement",
        "description": "Contact patients who are due for prescription refills. Sends personalised reminders via SMS or email. Use when asked about patient outreach, reminders, or refills.",
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
            },
            "required": [],
        },
    },
]

ORCHESTRATOR_SYSTEM = """You are the Orchestrator Agent for PharmAgent AI — a multi-agent pharmacy management system.

Your job is to:
1. Understand the pharmacist's request
2. Decide which specialist agents to call (you can call multiple)
3. Synthesise all results into a clear, actionable summary for the pharmacist

Available agents:
- check_drug_interactions: for patient-specific medication safety checks
- run_stock_review: for inventory management
- run_patient_engagement: for patient refill reminders

Always respond professionally. After calling agents, summarise findings clearly with any urgent actions highlighted.
If something requires immediate pharmacist attention (e.g. a critical drug interaction), call that out at the top."""


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

            if tool_name == "check_drug_interactions":
                result = check_interactions(tool_input["nhs_number"])
                agent_results["interaction_check"] = result

            elif tool_name == "run_stock_review":
                stock = run_stock_review()
                result = stock["analysis"]
                if stock["orders_placed"]:
                    result += f"\n\nAuto-orders placed: {len(stock['orders_placed'])} reorders triggered."
                agent_results["stock_review"] = result

            elif tool_name == "run_patient_engagement":
                days = tool_input.get("days_ahead", 7)
                channel = tool_input.get("channel", "sms")
                engagement = run_engagement_campaign(days_ahead=days, channel=channel)
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
