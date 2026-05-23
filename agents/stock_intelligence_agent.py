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
from tools.pharmacy_tools import (get_low_stock_items, get_expiring_stock,
                                   place_reorder, log_audit_event)
from config import MODEL

SYSTEM_PROMPT = """You are the Stock Intelligence Agent for PharmAgent AI.

Your role is to review pharmacy inventory data and make intelligent restocking decisions.

When you receive stock data:
1. List all low-stock items (below reorder threshold) — state quantity vs threshold
2. List all items expiring within 30 days — flag financial waste risk
3. For low-stock items, recommend a reorder and specify: medication name, quantity, supplier
4. For expiring stock, recommend whether to use, discount, or return to supplier
5. Provide a priority action list: IMMEDIATE (today) | THIS WEEK | NEXT 2 WEEKS

Be concise and operational. Pharmacy managers need clear, actionable output.
Format your reorder recommendations as a structured list so they can be actioned quickly."""


def run_stock_review() -> dict:
    client = anthropic.Anthropic()
    low_stock = get_low_stock_items()
    expiring = get_expiring_stock(days_ahead=30)

    context = f"""
Current Date: {__import__('datetime').datetime.today().strftime('%Y-%m-%d')}

LOW STOCK ITEMS (below reorder threshold):
{json.dumps(low_stock, indent=2)}

ITEMS EXPIRING WITHIN 30 DAYS:
{json.dumps(expiring, indent=2)}

Please review this inventory data and provide your stock management recommendations.
For each low-stock item, explicitly state: REORDER [medication] | [quantity] units | [supplier]
"""

    response = client.messages.create(
        model=MODEL,
        max_tokens=1000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": context}],
    )

    analysis = response.content[0].text

    # Auto-place reorders for critical low stock (below 20 units)
    orders_placed = []
    for item in low_stock:
        if item["quantity"] < 20:
            order = place_reorder(
                medication_name=item["medication"],
                quantity=item["reorder_quantity"],
                supplier=item["supplier"],
            )
            orders_placed.append(order)

    log_audit_event(
        agent="StockIntelligenceAgent",
        action="STOCK_REVIEW",
        details=f"Low stock: {len(low_stock)} items | Expiring: {len(expiring)} items | Auto-orders: {len(orders_placed)}",
    )

    return {
        "analysis": analysis,
        "low_stock_count": len(low_stock),
        "expiring_count": len(expiring),
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