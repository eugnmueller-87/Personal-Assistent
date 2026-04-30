import os
import json
import base64
import logging
from datetime import datetime
from collections import defaultdict
import anthropic
from skills import get_all_tools, call_tool

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

_history = defaultdict(list)
MAX_HISTORY = 10

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

_COMPLEX_SIGNALS = [
    " and ", " also ", " plus ", " both ", " with ",
    "explain", "analyz", "summari", "compar", "priorit",
    "suggest", "recommend", "what should", "help me",
    "what did we", "remember", "last time", "context",
    "urgent", "overview", "everything", "decision",
    "why", "how does", "what's the difference",
]

_SIMPLE_KEYWORDS = [
    "calendar", "emails", "email", "inbox", "issues",
    "tasks", "roadmap", "schedule", "events",
]


def _pick_model(message: str) -> str:
    msg = message.lower()
    words = msg.split()
    if any(signal in msg for signal in _COMPLEX_SIGNALS):
        return SONNET
    if len(words) > 12:
        return SONNET
    if len(words) <= 5:
        return HAIKU
    if any(kw in msg for kw in _SIMPLE_KEYWORDS):
        return HAIKU
    return SONNET


def route(user_message: str, user_id: str = "default") -> str:
    model = _pick_model(user_message)
    logging.info(f"[ICARUS] model={model.split('-')[1]} msg={user_message[:60]!r}")

    now = datetime.now()
    system = (
        f"You are ICARUS, a sharp personal assistant. "
        f"Today is {now.strftime('%A, %d %B %Y')} and the time is {now.strftime('%H:%M')}.\n\n"
        "You have tools to read the user's calendar, emails, GitHub issues, and roadmaps, "
        "and to create new tasks. Use them whenever the request involves real data.\n\n"
        "Email tool rules — follow strictly:\n"
        "- get_emails: general inbox check ('any emails?', 'what's new'). Unread + important only.\n"
        "- search_emails: whenever the user mentions a person, subject, sent mail, or older email.\n"
        "- get_email_body: whenever the user wants to READ an email ('show me', 'what did she write?', "
        "'what does it say?'). Use the message ID from search results. NEVER say you can't show the content — "
        "just call get_email_body. If you already have a message ID in context, call it immediately.\n\n"
        "When the user says 'show me the email' or similar and context already contains a message ID "
        "or a named sender, call get_email_body directly — do not ask for clarification.\n\n"
        "Only ask a clarifying question when you have no context at all to go on.\n\n"
        "Be concise and direct. No unnecessary filler. No markdown formatting — plain text only."
    )

    tools = get_all_tools()

    _load_history(user_id)
    history = _history[user_id]
    history.append({"role": "user", "content": user_message})

    response = client.messages.create(
        model=model,
        max_tokens=1024,
        system=system,
        tools=tools,
        messages=history,
    )

    while response.stop_reason == "tool_use":
        assistant_content = response.content
        tool_results = []

        for block in assistant_content:
            if block.type == "tool_use":
                result = call_tool(block.name, block.input, user_id)
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
            tools=tools,
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
    now = datetime.now()
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
