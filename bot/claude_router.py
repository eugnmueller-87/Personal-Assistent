import os
import json
import base64
import logging
from datetime import datetime
from collections import defaultdict
import anthropic
from google_client import get_this_week_events, get_unread_emails, create_calendar_event, get_email_details, send_reply
from github_client import get_open_issues, create_issue, get_roadmap

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

_history = defaultdict(list)
MAX_HISTORY = 10
_pending_replies: dict = {}
_edit_mode: set = set()

# --- Persistent memory via Upstash Redis ---
_redis = None

def _get_redis():
    global _redis
    if _redis is None:
        url = os.environ.get("UPSTASH_REDIS_URL")
        token = os.environ.get("UPSTASH_REDIS_TOKEN")
        if url and token:
            try:
                from upstash_redis import Redis
                _redis = Redis(url=url, token=token)
            except Exception as e:
                logging.warning(f"[ICARUS] Redis init failed: {e}")
    return _redis

def _clean_for_storage(history: list) -> list:
    clean = []
    for msg in history:
        if msg["role"] == "user" and isinstance(msg["content"], str):
            clean.append({"role": "user", "content": msg["content"]})
        elif msg["role"] == "assistant":
            content = msg["content"]
            text = None
            if isinstance(content, str):
                text = content
            elif isinstance(content, list):
                text = next((b.text for b in content if hasattr(b, "text")), None)
            if text:
                clean.append({"role": "assistant", "content": text})
    return clean[-MAX_HISTORY * 2:]

def _load_history(user_id: str):
    if _history[user_id]:
        return
    r = _get_redis()
    if not r:
        return
    try:
        data = r.get(f"icarus:history:{user_id}")
        if data:
            _history[user_id] = json.loads(data)
    except Exception as e:
        logging.warning(f"[ICARUS] Redis load failed: {e}")

def _save_history(user_id: str):
    r = _get_redis()
    if not r:
        return
    try:
        r.set(f"icarus:history:{user_id}", json.dumps(_clean_for_storage(_history[user_id])))
    except Exception as e:
        logging.warning(f"[ICARUS] Redis save failed: {e}")

HAIKU = "claude-haiku-4-5-20251001"
SONNET = "claude-sonnet-4-6"

# Signals that the message needs deeper reasoning — route to Sonnet
_COMPLEX_SIGNALS = [
    " and ", " also ", " plus ", " both ", " with ",
    "explain", "analyz", "summari", "compar", "priorit",
    "suggest", "recommend", "what should", "help me",
    "what did we", "remember", "last time", "context",
    "urgent", "overview", "everything", "decision",
    "why", "how does", "what's the difference",
]

# Keywords that indicate a single-intent data fetch — safe for Haiku
_SIMPLE_KEYWORDS = [
    "calendar", "emails", "email", "inbox", "issues",
    "tasks", "roadmap", "schedule", "events",
]


def _pick_model(message: str) -> str:
    msg = message.lower()
    words = msg.split()

    # Complex reasoning signals → Sonnet
    if any(signal in msg for signal in _COMPLEX_SIGNALS):
        return SONNET

    # Long messages need nuanced handling → Sonnet
    if len(words) > 12:
        return SONNET

    # Very short messages with no complexity → Haiku
    if len(words) <= 5:
        return HAIKU

    # Single-intent data requests → Haiku
    if any(kw in msg for kw in _SIMPLE_KEYWORDS):
        return HAIKU

    return SONNET


TOOLS = [
    {
        "name": "get_calendar",
        "description": "Get the user's calendar events for the next 7 days.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "get_emails",
        "description": "Get unread important emails from the user's Gmail inbox. Defaults to last 3 days.",
        "input_schema": {
            "type": "object",
            "properties": {
                "max_results": {
                    "type": "integer",
                    "description": "How many emails to fetch. Default 10.",
                },
                "since_minutes": {
                    "type": "integer",
                    "description": "Only fetch emails from the last N minutes. Use 10 for 'last 10 minutes', 60 for 'last hour', 1440 for 'today'.",
                },
            },
            "required": [],
        },
    },
    {
        "name": "get_issues",
        "description": "Get open GitHub issues from the user's repo.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "get_roadmap",
        "description": "Get the roadmap for a project.",
        "input_schema": {
            "type": "object",
            "properties": {
                "project": {
                    "type": "string",
                    "description": "Project name. Options: org-eugen, spendlens, icarus, agents.",
                }
            },
            "required": [],
        },
    },
    {
        "name": "create_issue",
        "description": "Create a new task or GitHub issue.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Short title of the task."},
                "body": {"type": "string", "description": "Optional description or details."},
            },
            "required": ["title"],
        },
    },
    {
        "name": "stage_email_reply",
        "description": (
            "Draft a reply to an email and stage it for user approval. "
            "The reply is NOT sent until the user confirms. "
            "Always use this when the user wants to reply to an email."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "message_id": {
                    "type": "string",
                    "description": "The Gmail message ID from the email list (shown as [ID:xxx]).",
                },
                "draft_body": {
                    "type": "string",
                    "description": "The reply text. Plain text, no markdown.",
                },
            },
            "required": ["message_id", "draft_body"],
        },
    },
    {
        "name": "create_calendar_event",
        "description": "Create an event on the user's Google Calendar.",
        "input_schema": {
            "type": "object",
            "properties": {
                "summary": {"type": "string", "description": "Event title."},
                "date": {"type": "string", "description": "Date in YYYY-MM-DD format."},
                "start_time": {"type": "string", "description": "Start time in HH:MM (24h). Omit for all-day events."},
                "end_time": {"type": "string", "description": "End time in HH:MM (24h). Defaults to 1 hour after start."},
            },
            "required": ["summary", "date"],
        },
    },
]


def _call_tool(name: str, inputs: dict, user_id: str = "default") -> str:
    try:
        if name == "get_calendar":
            return get_this_week_events()
        if name == "get_emails":
            return get_unread_emails(inputs.get("max_results", 10), inputs.get("since_minutes"))
        if name == "get_issues":
            return get_open_issues()
        if name == "get_roadmap":
            return get_roadmap(inputs.get("project", "org-eugen"))
        if name == "create_issue":
            return create_issue(inputs["title"], inputs.get("body", ""))
        if name == "create_calendar_event":
            return create_calendar_event(
                inputs["summary"],
                inputs["date"],
                inputs.get("start_time"),
                inputs.get("end_time"),
            )
        if name == "stage_email_reply":
            details = get_email_details(inputs["message_id"])
            _pending_replies[user_id] = {
                "thread_id": details["thread_id"],
                "to": details["to"],
                "subject": details["subject"],
                "in_reply_to": details["message_id_header"],
                "references": details["references"],
                "draft": inputs["draft_body"],
            }
            return f"Reply to {details['to']} staged for approval."
        return "Unknown tool."
    except Exception as e:
        logging.error(f"[ICARUS] tool '{name}' failed: {e}")
        return f"Tool unavailable ({name}): {e}"


def get_pending_reply(user_id: str) -> dict | None:
    return _pending_replies.get(user_id)


def clear_pending_reply(user_id: str):
    _pending_replies.pop(user_id, None)
    _edit_mode.discard(user_id)


def set_edit_mode(user_id: str):
    _edit_mode.add(user_id)


def is_edit_mode(user_id: str) -> bool:
    return user_id in _edit_mode


def update_pending_draft(user_id: str, new_draft: str):
    if user_id in _pending_replies:
        _pending_replies[user_id]["draft"] = new_draft
    _edit_mode.discard(user_id)


def confirm_send_reply(user_id: str) -> str:
    pending = _pending_replies.pop(user_id, None)
    if not pending:
        return "No pending reply found."
    try:
        return send_reply(
            pending["thread_id"],
            pending["to"],
            pending["subject"],
            pending["in_reply_to"],
            pending["references"],
            pending["draft"],
        )
    except Exception as e:
        logging.error(f"[ICARUS] send_reply failed: {e}")
        return f"Failed to send: {e}"


def route(user_message: str, user_id: str = "default") -> str:
    model = _pick_model(user_message)
    logging.info(f"[ICARUS] model={model.split('-')[1]} msg={user_message[:60]!r}")

    now = datetime.now()
    system = (
        f"You are ICARUS, a sharp personal assistant. "
        f"Today is {now.strftime('%A, %d %B %Y')} and the time is {now.strftime('%H:%M')}.\n\n"
        "You have tools to read the user's calendar, emails, GitHub issues, and roadmaps, "
        "and to create new tasks. Use them whenever the request involves real data.\n\n"
        "If a request is ambiguous or missing details, ask one short clarifying question "
        "instead of guessing or doing nothing.\n\n"
        "Be concise and direct. No unnecessary filler. No markdown formatting — plain text only."
    )

    _load_history(user_id)
    history = _history[user_id]
    history.append({"role": "user", "content": user_message})

    response = client.messages.create(
        model=model,
        max_tokens=1024,
        system=system,
        tools=TOOLS,
        messages=history,
    )

    while response.stop_reason == "tool_use":
        assistant_content = response.content
        tool_results = []

        for block in assistant_content:
            if block.type == "tool_use":
                result = _call_tool(block.name, block.input, user_id)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result,
                })

        history.append({"role": "assistant", "content": assistant_content})
        history.append({"role": "user", "content": tool_results})

        response = client.messages.create(
            model=model,
            max_tokens=1024,
            system=system,
            tools=TOOLS,
            messages=history,
        )

    final = next(
        (block.text for block in response.content if hasattr(block, "text")),
        "I didn't catch that — can you rephrase?",
    )

    history.append({"role": "assistant", "content": response.content})

    if len(history) > MAX_HISTORY * 2:
        _history[user_id] = history[-(MAX_HISTORY * 2):]

    _save_history(user_id)
    return final


def compose_morning_brief(cal: str, mail: str, issues: str) -> str:
    from datetime import datetime
    from zoneinfo import ZoneInfo
    now = datetime.now(ZoneInfo("Europe/Berlin"))

    response = client.messages.create(
        model=SONNET,
        max_tokens=512,
        messages=[{
            "role": "user",
            "content": (
                f"You are ICARUS. Write a sharp morning briefing for {now.strftime('%A, %d %B %Y')}. "
                "Be direct and useful. No filler, no markdown, plain text only. "
                "Lead with what matters most today.\n\n"
                f"Today's calendar:\n{cal}\n\n"
                f"Inbox (last 24h):\n{mail}\n\n"
                f"Open tasks:\n{issues}"
            ),
        }],
    )
    return next(
        (block.text for block in response.content if hasattr(block, "text")),
        "Good morning. Couldn't pull your data — check your connections.",
    )


def is_email_urgent(formatted_emails: str) -> bool:
    response = client.messages.create(
        model=HAIKU,
        max_tokens=10,
        messages=[{
            "role": "user",
            "content": (
                f"New emails:\n{formatted_emails}\n\n"
                "Reply YES if any requires action today. Reply NO if they can wait. One word only."
            ),
        }],
    )
    return "YES" in next(
        (block.text for block in response.content if hasattr(block, "text")), "NO"
    ).upper()


def route_image(image_bytes: bytes, caption: str = "", user_id: str = "default") -> str:
    logging.info(f"[ICARUS] model=sonnet image={len(image_bytes)//1024}KB caption={caption!r}")

    prompt = caption if caption else (
        "Analyze this image. Extract all key information: numbers, names, dates, "
        "totals, decisions, or any actionable content. Be concise."
    )

    now = datetime.now()
    system = (
        f"You are ICARUS, a sharp personal assistant. "
        f"Today is {now.strftime('%A, %d %B %Y')} and the time is {now.strftime('%H:%M')}.\n\n"
        "Be concise and direct. No unnecessary filler. No markdown formatting — plain text only."
    )

    image_data = base64.standard_b64encode(image_bytes).decode("utf-8")

    response = client.messages.create(
        model=SONNET,
        max_tokens=1024,
        system=system,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/jpeg",
                        "data": image_data,
                    },
                },
                {"type": "text", "text": prompt},
            ],
        }],
    )

    return next(
        (block.text for block in response.content if hasattr(block, "text")),
        "Couldn't analyze the image.",
    )
