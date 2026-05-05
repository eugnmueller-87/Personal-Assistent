import os
import requests

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
        "name": "hermes_greet",
        "description": (
            "Ask Hermes to introduce himself and share his current status. "
            "Use when the user asks Icarus to greet Hermes, check if Hermes is alive, "
            "or wants to know what Hermes is currently tracking."
        ),
        "input_schema": {"type": "object", "properties": {}, "required": []},
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


def _get_url() -> tuple[str, str | None]:
    """Returns (url, error). Error is set if URL is missing or malformed."""
    raw = os.environ.get("HERMES_URL", "").strip().rstrip("/")
    if not raw:
        return "", "HERMES_URL is not set in environment."
    if not raw.startswith("http"):
        return "", f"HERMES_URL is misconfigured (got: '{raw[:60]}') — must start with https://"
    return raw, None


def _headers():
    return {"x-api-key": HERMES_API_KEY} if HERMES_API_KEY else {}


def _format_item(item: dict) -> str:
    emoji = item.get("emoji", "📰")
    urgency = item.get("urgency", "")
    supplier = item.get("supplier", "")
    title = item.get("title", "")[:120]
    date = item.get("published", "")[:10]
    reason = item.get("significance_reason", "")
    line = f"{emoji} [{urgency}] {supplier} — {title} ({date})"
    if reason:
        line += f"\n   {reason[:120]}"
    return line


def _build_miro_board(board_type: str, category: str = None) -> str:
    url, err = _get_url()
    if err:
        return err
    params = {}
    if category and board_type == "landscape":
        params["category"] = category
    try:
        r = requests.post(f"{url}/miro/{board_type}", params=params, headers=_headers(), timeout=120)
        r.raise_for_status()
        label = f" ({category})" if category else ""
        return f"Miro {board_type} board{label} ready: {r.json()['url']}"
    except Exception as e:
        return f"Miro board failed: {e}"


def _hermes_query(company: str, limit: int = 5) -> str:
    url, err = _get_url()
    if err:
        return err
    try:
        r = requests.get(f"{url}/query/{company}", params={"limit": limit}, headers=_headers(), timeout=15)
        r.raise_for_status()
        data = r.json()
        signals = data.get("signals", [])
        if not signals:
            return data.get("message", f"No signals found for {company}.")
        lines = [f"Hermes — {data['company']} ({len(signals)} signals):"]
        for item in signals:
            lines.append(_format_item(item))
        return "\n".join(lines)
    except Exception as e:
        return f"Hermes query failed: {e}"


def _hermes_briefing(limit: int = 10) -> str:
    url, err = _get_url()
    if err:
        return err
    try:
        r = requests.get(f"{url}/briefing", params={"limit": limit}, headers=_headers(), timeout=15)
        r.raise_for_status()
        data = r.json()
        signals = data.get("signals", [])
        if not signals:
            return "No significant Hermes signals yet — data accumulates as crawlers run."
        lines = [f"Hermes briefing — top {len(signals)} signals:"]
        for item in signals:
            lines.append(_format_item(item))
        return "\n".join(lines)
    except Exception as e:
        return f"Hermes briefing failed: {e}"


def _hermes_greet() -> str:
    url, err = _get_url()
    if err:
        return err
    try:
        r = requests.get(f"{url}/greet", timeout=10)
        r.raise_for_status()
        data = r.json()
        return f"{data['message']}\n\n{data['latest']}"
    except Exception as e:
        return f"Hermes did not respond: {e}"


def handle(name: str, inputs: dict, user_id: str = "default"):
    if name == "hermes_greet":
        return _hermes_greet()
    if name == "build_miro_board":
        return _build_miro_board(inputs.get("board_type", "landscape"), inputs.get("category"))
    if name == "hermes_query":
        return _hermes_query(inputs["company"], inputs.get("limit", 5))
    if name == "hermes_briefing":
        return _hermes_briefing(inputs.get("limit", 10))
    return None
