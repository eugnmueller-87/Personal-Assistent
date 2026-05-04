import os
import json
import requests
from difflib import get_close_matches

HERMES_URL = os.environ.get("HERMES_URL", "").rstrip("/")
HERMES_API_KEY = os.environ.get("HERMES_API_KEY", "")

TOOLS = [
    {
        "name": "build_miro_board",
        "description": (
            "Build a Miro visual board from Hermes market intelligence data. "
            "Use when the user asks to build, create, or generate a Miro board, "
            "supplier landscape, signal board, or market intelligence visualization."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "board_type": {
                    "type": "string",
                    "enum": ["landscape", "signals"],
                    "description": (
                        "landscape = all tracked suppliers grouped by category. "
                        "signals = today's significant market signals grouped by signal type."
                    ),
                },
                "category": {
                    "type": "string",
                    "description": (
                        "Optional. Filter landscape board to one category. "
                        "Examples: 'AI Foundation Labs', 'Semiconductors & Chips', 'Cloud & Infrastructure'."
                    ),
                },
            },
            "required": ["board_type"],
        },
    },
    {
        "name": "hermes_query",
        "description": (
            "Query Hermes market intelligence for a specific company or supplier. "
            "Use when the user asks what Hermes has on a company, wants recent signals "
            "for a supplier, or asks about market news for a specific company."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "company": {
                    "type": "string",
                    "description": "Company name to look up, e.g. 'NVIDIA', 'TSMC', 'OpenAI'.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max signals to return. Default 5.",
                },
            },
            "required": ["company"],
        },
    },
    {
        "name": "hermes_briefing",
        "description": (
            "Get the latest significant market intelligence signals from Hermes "
            "across all tracked suppliers. Use when the user asks for a Hermes briefing, "
            "market overview, top signals, or what's moving in the market today."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Max signals to return. Default 10.",
                },
            },
            "required": [],
        },
    },
]


def _redis():
    url = os.environ.get("UPSTASH_REDIS_URL")
    token = os.environ.get("UPSTASH_REDIS_TOKEN")
    if not (url and token):
        return None
    from upstash_redis import Redis
    return Redis(url=url, token=token)


def _format_item(item: dict) -> str:
    emoji = item.get("emoji", "📰")
    urgency = item.get("urgency", "")
    signal = item.get("signal_type", "OTHER")
    supplier = item.get("supplier", "")
    title = item.get("title", "")[:120]
    date = item.get("published", "")[:10]
    reason = item.get("significance_reason", "")
    line = f"{emoji} [{urgency}] {supplier} — {title} ({date})"
    if reason:
        line += f"\n   {reason[:120]}"
    return line


def _build_miro_board(board_type: str, category: str = None) -> str:
    if not HERMES_URL:
        return "HERMES_URL not set — add it to your environment variables."
    endpoint = f"{HERMES_URL}/miro/{board_type}"
    params = {}
    if category and board_type == "landscape":
        params["category"] = category
    headers = {"x-api-key": HERMES_API_KEY} if HERMES_API_KEY else {}
    try:
        r = requests.post(endpoint, params=params, headers=headers, timeout=120)
        r.raise_for_status()
        data = r.json()
        label = f" ({category})" if category else ""
        return f"Miro {board_type} board{label} ready: {data['url']}"
    except Exception as e:
        return f"Miro board failed: {e}"


def _hermes_query(company: str, limit: int = 5) -> str:
    r = _redis()
    if not r:
        return "Redis not available."
    slug = company.lower().strip().replace(" ", "_").replace("-", "_").replace(".", "_")
    if not r.exists(f"hermes:supplier:{slug}"):
        keys = r.keys("hermes:supplier:*")
        known = [k.replace("hermes:supplier:", "") for k in keys]
        matches = get_close_matches(slug, known, n=1, cutoff=0.6)
        if not matches:
            return f"No Hermes data found for '{company}'. It may not be tracked yet."
        slug = matches[0]
    ids = r.lrange(f"hermes:supplier:{slug}", 0, limit - 1)
    if not ids:
        return f"No signals yet for {company}."
    lines = [f"Hermes — {slug.replace('_', ' ').title()} (last {len(ids)} signals):"]
    for item_id in ids:
        raw = r.get(f"hermes:item:{item_id}")
        if raw:
            lines.append(_format_item(json.loads(raw)))
    return "\n".join(lines)


def _hermes_briefing(limit: int = 10) -> str:
    r = _redis()
    if not r:
        return "Redis not available."
    keys = r.keys("hermes:item:*")
    items = []
    for key in keys[:300]:
        raw = r.get(key)
        if raw:
            item = json.loads(raw)
            if item.get("is_significant"):
                items.append(item)
    items.sort(key=lambda x: x.get("published", ""), reverse=True)
    items = items[:limit]
    if not items:
        return "No significant Hermes signals yet — data accumulates as crawlers run."
    lines = [f"Hermes briefing — top {len(items)} signals:"]
    for item in items:
        lines.append(_format_item(item))
    return "\n".join(lines)


def handle(name: str, inputs: dict, user_id: str = "default"):
    if name == "build_miro_board":
        return _build_miro_board(inputs.get("board_type", "landscape"), inputs.get("category"))
    if name == "hermes_query":
        return _hermes_query(inputs["company"], inputs.get("limit", 5))
    if name == "hermes_briefing":
        return _hermes_briefing(inputs.get("limit", 10))
    return None
