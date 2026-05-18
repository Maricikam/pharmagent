"""
PharmAgent AI — Demo Script
Run this to see all agents working live.

Usage:
    cd pharmagent
    python run_demo.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db.database import init_db
from scripts.seed import seed


def main():
    print("=" * 65)
    print("  PharmAgent AI — Live Demo")
    print("  DataVita Infrastructure Proposal | NCLan HND Software Dev")
    print("=" * 65)

    print("\n📦 Initialising database and seeding data...")
    seed()

    print("\n" + "─" * 65)
    print("DEMO 1 — Morning pharmacy system check via Orchestrator")
    print("─" * 65)
    from agents.orchestrator_agent import run_orchestrator
    result1 = run_orchestrator(
        "Good morning. Please do a full stock review and send SMS reminders "
        "to any patients whose prescriptions are due in the next 5 days."
    )
    print("\n📋 Orchestrator Response:")
    print(result1)

    print("\n" + "─" * 65)
    print("DEMO 2 — Patient interaction safety check")
    print("─" * 65)
    result2 = run_orchestrator(
        "Check Thomas Robertson — NHS 4756019283 — before I dispense. "
        "He's on warfarin, I need to know if there are any interaction risks."
    )
    print("\n📋 Orchestrator Response:")
    print(result2)

    print("\n" + "─" * 65)
    print("DEMO 3 — Standalone Interaction Safety Agent")
    print("─" * 65)
    from agents.interaction_safety_agent import check_interactions
    print("Checking Margaret Campbell (warfarin + aspirin)...")
    print(check_interactions("4823719056"))

    print("\n" + "─" * 65)
    print("DEMO 4 — Stock Intelligence Agent")
    print("─" * 65)
    from agents.stock_intelligence_agent import run_stock_review
    stock = run_stock_review()
    print(stock["analysis"])
    if stock["orders_placed"]:
        print("\n✅ Auto-orders placed:")
        for o in stock["orders_placed"]:
            print(f"   {o['medication']} x{o['quantity']} | {o['supplier']} | Ref: {o['reference']}")

    print("\n" + "─" * 65)
    print("DEMO 5 — Patient Engagement Agent")
    print("─" * 65)
    from agents.patient_engagement_agent import run_engagement_campaign
    eng = run_engagement_campaign(days_ahead=7, channel="sms")
    print(f"Contacted {eng['patients_contacted']} patients via SMS\n")
    for r in eng["results"]:
        print(f"  👤 {r['patient']}: {r['message'][:100]}...")

    print("\n" + "─" * 65)
    print("DEMO 6 — Audit Trail")
    print("─" * 65)
    from tools.pharmacy_tools import get_recent_audit_logs
    logs = get_recent_audit_logs(limit=8)
    for log in logs:
        print(f"  [{log['timestamp'][:19]}] {log['agent']} | {log['action']}")
        print(f"    {log['details'][:80]}...")
        print()

    print("=" * 65)
    print("  Demo complete. All agents operational.")
    print("=" * 65)


if __name__ == "__main__":
    main()