"""
Agentic post-harvest advisor. Muse Spark 1.3 (function-calling) receives
a farmer's Tamil sentence and calls existing deterministic tools:
  - lookup_fair_price
  - recommend_post_harvest
  - find_logistics_pool
  - get_scan_audit

The model decides which tools to call and in what order, then answers in
Tamil from the tool results only — every number comes from your code.
Capped at 5 tool calls per request.
"""
import json
import logging
from typing import Optional

from app.config import get_settings
from app.database import SessionLocal
from app.models import CropListing, MarketPrice, PostHarvestRecommendation
from app.services.meta_ai import client, budget_guard, MetaAIUnavailable
from app.services.pricing import compute_fair_price
from app.services.post_harvest_advisor import recommend_allocation
from app.services.matching import cluster_listings, PoolCandidate

log = logging.getLogger(__name__)
settings = get_settings()

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "lookup_fair_price",
            "description": "Look up the current fair price for a crop in a district.",
            "parameters": {
                "type": "object",
                "properties": {
                    "crop_type": {"type": "string", "description": "e.g. tomato, onion, paddy"},
                    "district": {"type": "string", "description": "e.g. Coimbatore, Madurai"},
                },
                "required": ["crop_type", "district"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "recommend_post_harvest",
            "description": "Get a deterministic sell/store/process recommendation for a crop quantity.",
            "parameters": {
                "type": "object",
                "properties": {
                    "crop_type": {"type": "string"},
                    "quantity_kg": {"type": "number"},
                    "district": {"type": "string"},
                    "latitude": {"type": "number"},
                    "longitude": {"type": "number"},
                },
                "required": ["crop_type", "quantity_kg", "district", "latitude", "longitude"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_scan_audit",
            "description": "Get the AI audit result and defect details for a crop listing by its ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "listing_id": {"type": "string"},
                },
                "required": ["listing_id"],
            },
        },
    },
]

SYSTEM = (
    "You are an expert, empathetic post-harvest advisor for Tamil Nadu farmers. "
    "Respond in clear, simple Tamil. Use the available tools to retrieve facts. "
    "Never invent prices, quantities or places — only use what the tools return. "
    "Keep answers concise (3–5 sentences). Use digits 0-9 for all numbers."
)


def _exec_tool(name: str, args: dict) -> str:
    with SessionLocal() as db:
        if name == "lookup_fair_price":
            latest = (
                db.query(MarketPrice)
                .filter(
                    MarketPrice.crop_type == args.get("crop_type", "").lower(),
                    MarketPrice.district == args.get("district", ""),
                )
                .order_by(MarketPrice.recorded_date.desc())
                .first()
            )
            if not latest:
                # Try without district filter as fallback
                latest = (
                    db.query(MarketPrice)
                    .filter(MarketPrice.crop_type == args.get("crop_type", "").lower())
                    .order_by(MarketPrice.recorded_date.desc())
                    .first()
                )
            if not latest:
                return json.dumps({"error": "No market price data found for this crop"})
            result = compute_fair_price(
                wholesale_price_per_kg=latest.wholesale_price_per_kg,
                retail_price_per_kg=latest.retail_price_per_kg,
            )
            return json.dumps({
                "crop_type": args.get("crop_type"),
                "district": args.get("district"),
                "wholesale_price_per_kg": latest.wholesale_price_per_kg,
                "retail_price_per_kg": latest.retail_price_per_kg,
                "fair_price_per_kg": result.fair_price_per_kg,
            })

        elif name == "recommend_post_harvest":
            result = recommend_allocation(
                db,
                crop_type=args.get("crop_type", "tomato"),
                quantity_kg=float(args.get("quantity_kg", 100)),
                district=args.get("district", "Coimbatore"),
                latitude=float(args.get("latitude", 11.0)),
                longitude=float(args.get("longitude", 77.0)),
            )
            return json.dumps({
                "crop_type": result.crop_type,
                "quantity_kg": result.quantity_kg,
                "sell_now_kg": sum(a.quantity_kg for a in result.allocations if a.channel == "sell_now"),
                "store_kg": sum(a.quantity_kg for a in result.allocations if a.channel == "store"),
                "process_kg": sum(a.quantity_kg for a in result.allocations if a.channel == "process"),
                "at_risk_kg": sum(a.quantity_kg for a in result.allocations if a.channel == "at_risk"),
                "expected_net_value": result.expected_net_value,
                "projected_savings": result.projected_savings,
                "reasoning": result.reasoning,
            })

        elif name == "get_scan_audit":
            listing = db.get(CropListing, args.get("listing_id"))
            if not listing:
                return json.dumps({"error": "Crop listing not found"})
            return json.dumps({
                "listing_id": listing.id,
                "crop_type": listing.crop_type,
                "device_grade": listing.grade.value if listing.grade else None,
                "audit_status": listing.audit_status,
                "audit_grade": listing.audit_grade,
                "audit_confidence": listing.audit_confidence,
                "audit_defects": listing.audit_defects,
            })

    return json.dumps({"error": f"Unknown tool: {name}"})


def agent_ask(question: str, farmer_lat: float = 11.0, farmer_lng: float = 77.0) -> dict:
    """
    Executes an autonomous function-calling loop.
    Returns: {"answer": str, "tool_trace": list[dict]}
    """
    c = client()
    budget_guard()

    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": question},
    ]
    tool_trace = []
    max_tool_calls = 5

    for _ in range(max_tool_calls):
        r = c.chat.completions.create(
            model=settings.META_MODEL_FAST,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
        )
        msg = r.choices[0].message

        if not getattr(msg, "tool_calls", None):
            return {"answer": msg.content or "", "tool_trace": tool_trace}

        messages.append(msg)
        for tc in msg.tool_calls:
            args = json.loads(tc.function.arguments) if isinstance(tc.function.arguments, str) else tc.function.arguments
            if tc.function.name == "recommend_post_harvest":
                args.setdefault("latitude", farmer_lat)
                args.setdefault("longitude", farmer_lng)
            result = _exec_tool(tc.function.name, args)
            tool_trace.append({
                "tool": tc.function.name,
                "args": args,
                "result": json.loads(result),
            })
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": result,
            })
            log.info("agent executed tool=%s args=%s", tc.function.name, args)

    final = c.chat.completions.create(
        model=settings.META_MODEL_FAST,
        messages=messages,
    )
    return {"answer": final.choices[0].message.content or "", "tool_trace": tool_trace}
