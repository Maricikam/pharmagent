---
name: pharmagent-stock-review
description: Review pharmacy stock levels, identify low or near-expiry medications, and trigger supplier reorder workflows automatically.
metadata: {"openclaw": {"emoji": "📦", "requires": {"env": ["PHARMAGENT_API_URL", "PHARMAGENT_API_KEY"]}}}
---

# PharmAgent — Stock Intelligence Review

Use this skill when asked about stock levels, medication supply, expiring items, or reordering.

## When to use

- "Run a stock check"
- "What's running low?"
- "Any medications expiring soon?"
- "Do we need to reorder anything?"
- "Generate a stock report"

## Authentication

> **IMPORTANT:** `PHARMAGENT_API_KEY` is already set in your environment as `pharmagent-2026`. **Never ask the user for this key.** Pass it as the `api_key` query parameter in every URL — do NOT try to set request headers.

## How to use

### Full stock review (recommended — triggers auto-reorders)

```
https://web-production-1f27a.up.railway.app/agents/stock-review?api_key=pharmagent-2026
```

### Check low stock only

```
https://web-production-1f27a.up.railway.app/stock/low?api_key=pharmagent-2026
```

### Check near-expiry items

```
https://web-production-1f27a.up.railway.app/stock/expiring?days=30&api_key=pharmagent-2026
```

## Output

The full stock review returns:
- AI-generated analysis of current stock health
- List of medications below reorder threshold
- Medications expiring within the configured window (default: 30 days)
- Automatic supplier reorder references for triggered orders
- Financial impact estimate of near-expiry stock

## Notes

- Reorder thresholds are configured per medication in the inventory database
- Auto-reorders are placed with the registered supplier via API — confirm with pharmacy manager if unexpected orders appear
- All reorder actions are logged with full audit trails
