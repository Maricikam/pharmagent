"""
PharmAgent AI — Demo Script
Run this to see all agents working live.

Usage:
    cd pharmagent
    python run_demo.py

No ANTHROPIC_API_KEY? The script prints sample output so you can see the
shape of each agent's response without setting up credentials first.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

LIVE = bool(os.getenv("ANTHROPIC_API_KEY"))

DEMO_INTERACTION = """
INTERACTION SAFETY REPORT — Margaret Campbell
Active medications: Warfarin 5mg, Atenolol 50mg, Lisinopril 10mg
New medication requested: Ibuprofen 400mg

⚠️  HIGH RISK — DO NOT DISPENSE WITHOUT PHARMACIST REVIEW
Warfarin + Ibuprofen: NSAIDs significantly increase bleeding risk in patients
on anticoagulants. This interaction is rated HIGH in the clinical rules table.
The AI cannot downgrade this rating. Pharmacist sign-off required.
""".strip()

DEMO_STOCK = """
LOW STOCK ITEMS:
  • Metformin 500mg — 12 units (threshold: 50) → REORDER 200 units | AAH Pharmaceuticals
  • Amlodipine 5mg  — 8 units  (threshold: 30) → REORDER 100 units | Alliance Healthcare

EXPIRING WITHIN 30 DAYS:
  • Amoxicillin 250mg — 45 units expiring 2026-06-10 (est. waste: £18.90)

PRIORITY: Auto-reorder triggered for critical low-stock items.
""".strip()

DEMO_ENGAGEMENT = """
Contacted 3 patients via SMS:
  • Margaret Campbell — "Hi Margaret, your Warfarin prescription is due in 3 days..."
  • Susan Graham      — "Hi Susan, Renfrew Road Pharmacy: your Ramipril is due soon..."
  • William Stevenson — "Hi William, time to collect your Metformin. Call 0141 555 0199."
""".strip()


def section(title):
    print("\n" + "─" * 65)
    print(f"  {title}")
    print("─" * 65)


def main():
    print("=" * 65)
    print("  PharmAgent AI — Live Demo")
    print("  DataVita OpenClaw Challenge")
    if not LIVE:
        print("  ⚠️  Demo mode — set ANTHROPIC_API_KEY for live AI output")
    print("=" * 65)

    from db.database import init_db
    from scripts.seed import seed
    print("\nInitialising database and seeding test data...")
    seed()

    section("DEMO 1 — Drug Interaction Safety Check (Margaret Campbell)")
    if LIVE:
        from agents.interaction_safety_agent import check_interactions
        print(check_interactions("1203480016"))
    else:
        print(DEMO_INTERACTION)

    section("DEMO 2 — Stock Intelligence Agent")
    if LIVE:
        from agents.stock_intelligence_agent import run_stock_review
        stock = run_stock_review()
        print(stock["analysis"])
        if stock["orders_placed"]:
            print("\nAuto-orders placed:")
            for o in stock["orders_placed"]:
                print(f"  {o['medication']} x{o['quantity']} | {o['supplier']} | Ref: {o['reference']}")
    else:
        print(DEMO_STOCK)

    section("DEMO 3 — Patient Engagement Campaign (SMS refill reminders)")
    if LIVE:
        from agents.patient_engagement_agent import run_engagement_campaign
        eng = run_engagement_campaign(days_ahead=7, channel="sms")
        print(f"Contacted {eng['patients_contacted']} patients via SMS\n")
        for r in eng["results"]:
            print(f"  {r['patient']}: {r['message'][:100]}...")
    else:
        print(DEMO_ENGAGEMENT)

    section("DEMO 4 — Orchestrator (full daily briefing via single prompt)")
    if LIVE:
        from agents.orchestrator_agent import run_orchestrator
        result = run_orchestrator(
            "Good morning. Please do a full stock review and send SMS reminders "
            "to any patients whose prescriptions are due in the next 5 days."
        )
        print(result)
    else:
        print("Orchestrator would coordinate Stock + Engagement agents and synthesise a single briefing.")
        print("Run with ANTHROPIC_API_KEY set to see the live multi-agent output.")

    section("DEMO 5 — Audit Trail")
    from tools.pharmacy_tools import get_recent_audit_logs
    logs = get_recent_audit_logs(limit=6)
    for log in logs:
        print(f"  [{log['timestamp'][:19]}] {log['agent']} | {log['action']}")
        print(f"    {log['details'][:80]}")
        print()

    print("=" * 65)
    print("  Demo complete.")
    if not LIVE:
        print("  Set ANTHROPIC_API_KEY and re-run for live AI output.")
    print("=" * 65)


if __name__ == "__main__":
    main()
