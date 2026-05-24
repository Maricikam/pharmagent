"""
Stock Intelligence Agent — PharmAgent AI
==========================================
Monitors pharmacy inventory, identifies supply risks, and automates
supplier reorder workflows.

Responsibility:
    Reviews current stock levels against reorder thresholds, identifies
    medications approaching expiry within a configurable window, and
    triggers automated purchase orders with registered suppliers.

Tools used:
    - get_low_stock_items()      — medications below reorder threshold
    - get_near_expiry_items()    — medications expiring within window
    - place_supplier_order()     — trigger reorder with supplier API
    - log_audit_entry()          — write action to audit trail

Output:
    A stock health summary including low-stock list, near-expiry items
    with estimated waste value, and references for any auto-orders placed.

Design note:
    Follows the Observer pattern — reacts to inventory state rather than
    polling on a fixed schedule. All reorder actions are logged for
    regulatory audit compliance.
"""

import anthropic
import json
from datetime import datetime
from tools.pharmacy_tools import (get_low_stock_items, get_expiring_stock,
                                   get_prescription_demand, place_reorder,
                                   log_audit_event)
from config import MODEL

SYSTEM_PROMPT = """You are the Stock Intelligence Agent for PharmAgent AI.

Your role is to review pharmacy inventory data and make intelligent restocking decisions.

When you receive stock data:
1. List all low-stock items (below reorder threshold) — state quantity vs threshold
2. List all items expiring within 30 days — flag financial waste risk
3. SHORTAGE PREDICTION — for any medication where days_of_supply < 30, flag as a predicted shortage
   even if it is currently above the reorder threshold. State the number of days remaining.
4. INTELLIGENT ORDERING — for each low-stock or predicted-shortage item, recommend the
   smart_reorder_quantity (2-month demand buffer) rather than the fixed reorder_quantity
5. Provide a priority action list: [URGENT] / [TODAY] / [THIS WEEK]

Formatting rules:
- No emojis or decorative symbols
- Plain text only, suitable for a clinical handover report
- Use DD/MM/YYYY for dates
- Be concise and operational — pharmacy managers need clear, actionable output"""


def run_stock_review() -> dict:
    client = anthropic.Anthropic()
    low_stock = get_low_stock_items()
    expiring = get_expiring_stock(days_ahead=30)
    demand = get_prescription_demand()

    predicted_shortages = [
        d for d in demand
        if d.get("days_of_supply") is not None and d["days_of_supply"] < 30
        and not any(ls["medication"] == d["medication"] for ls in low_stock)
    ]

    context = f"""
Current Date: {datetime.today().strftime('%Y-%m-%d')}

LOW STOCK ITEMS (below reorder threshold):
{json.dumps(low_stock, indent=2)}

ITEMS EXPIRING WITHIN 30 DAYS:
{json.dumps(expiring, indent=2)}

PRESCRIPTION DEMAND AND DAYS OF SUPPLY:
{json.dumps(demand, indent=2)}

PREDICTED SHORTAGES (above threshold but < 30 days supply at current demand):
{json.dumps(predicted_shortages, indent=2)}

Review this inventory data. For each low-stock or predicted-shortage item, use the
smart_reorder_quantity field (2-month demand buffer) for your reorder recommendation.
Explicitly state: REORDER [medication] | [quantity] units | [supplier]
"""

    response = client.messages.create(
        model=MODEL,
        max_tokens=1200,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": context}],
    )

    analysis = response.content[0].text

    # Auto-place reorders for critical low stock (below 20 units), using smart quantity
    orders_placed = []
    for item in low_stock:
        if item["quantity"] < 20:
            med_demand = next((d for d in demand if d["medication"] == item["medication"]), None)
            smart_qty = med_demand["smart_reorder_quantity"] if med_demand else item["reorder_quantity"]
            order = place_reorder(
                medication_name=item["medication"],
                quantity=smart_qty,
                supplier=item["supplier"],
            )
            orders_placed.append(order)

    log_audit_event(
        agent="StockIntelligenceAgent",
        action="STOCK_REVIEW",
        details=f"Low stock: {len(low_stock)} | Expiring: {len(expiring)} | Predicted shortages: {len(predicted_shortages)} | Auto-orders: {len(orders_placed)}",
    )

    return {
        "analysis": analysis,
        "low_stock_count": len(low_stock),
        "expiring_count": len(expiring),
        "predicted_shortage_count": len(predicted_shortages),
        "orders_placed": orders_placed,
    }


if __name__ == "__main__":
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    print("=== Stock Intelligence Agent ===\n")
    result = run_stock_review()
    print(result["analysis"])
    if result["orders_placed"]:
        print("\n--- Auto-Orders Placed ---")
        for order in result["orders_placed"]:
            print(f"  ✅ {order['medication']} x{order['quantity']} | Ref: {order['reference']}")