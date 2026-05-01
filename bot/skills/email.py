import os
import json
import logging
from google_client import get_unread_emails, search_emails, get_email_body, get_email_details, send_reply

_pending_replies: dict = {}
_edit_mode: set = set()
_TTL = 86400  # 24h — pending approvals expire if not acted on

TOOLS = [
    {
        "name": "get_emails",
        "description": (
            "Quick inbox check — returns unread important emails from the last 3 days. "
            "Use this when the user wants a general update: 'any emails?', 'check my inbox', 'what's new'. "
            "Do NOT use this to find a specific email by person or subject — use search_emails for that."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "max_results": {
                    "type": "integer",
                    "description": "How many emails to fetch. Default 10.",
                },
                "since_minutes": {
                    "type": "integer",
                    "description": "Only fetch emails from the last N minutes. Use 60 for 'last hour', 1440 for 'today'.",
                },
            },
            "required": [],
        },
    },
    {
        "name": "search_emails",
        "description": (
            "Search for a specific email by person, subject, or folder. "
            "Use this when the user names someone ('email from Petra', 'my last email to Stefan'), "
            "mentions a subject, or asks for sent mail or older emails. "
            "Searches read AND unread, any folder. "
            "Supports Gmail syntax: 'from:name', 'to:name', 'subject:text', 'in:sent', "
            "'in:anywhere', 'newer_than:30d'. "
            "Never use get_emails for this — get_emails only sees unread/important."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Gmail search query, e.g. 'from:petra in:anywhere newer_than:30d'",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Max emails to return. Default 5.",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_email_body",
        "description": (
            "Fetch the full content of an email — sender name and the actual message text. "
            "Use this whenever the user wants to READ an email: 'show me the email', "
            "'what did she write?', 'what does it say?', 'read it'. "
            "Always call this after search_emails when the user wants to see the message — "
            "never say you can't show it, just call this tool."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "message_id": {
                    "type": "string",
                    "description": "The Gmail message ID (shown as [ID:xxx] in search results).",
                },
            },
            "required": ["message_id"],
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
]


def _get_redis():
    try:
        url = os.environ.get("UPSTASH_REDIS_URL")
        token = os.environ.get("UPSTASH_REDIS_TOKEN")
        if url and token:
            from upstash_redis import Redis
            return Redis(url=url, token=token)
    except Exception:
        pass
    return None


def handle(name: str, inputs: dict, user_id: str = "default"):
    if name == "get_emails":
        return get_unread_emails(inputs.get("max_results", 10), inputs.get("since_minutes"))
    if name == "search_emails":
        return search_emails(inputs["query"], inputs.get("max_results", 5))
    if name == "get_email_body":
        return get_email_body(inputs["message_id"])
    if name == "stage_email_reply":
        details = get_email_details(inputs["message_id"])
        pending = {
            "thread_id": details["thread_id"],
            "to": details["to"],
            "subject": details["subject"],
            "in_reply_to": details["message_id_header"],
            "references": details["references"],
            "draft": inputs["draft_body"],
        }
        r = _get_redis()
        if r:
            try:
                r.set(f"icarus:pending_reply:{user_id}", json.dumps(pending), ex=_TTL)
            except Exception as e:
                logging.warning(f"[EMAIL] Redis set failed: {e}")
                _pending_replies[user_id] = pending
        else:
            _pending_replies[user_id] = pending
        return f"Reply to {details['to']} staged for approval."
    return None


def get_pending_reply(user_id: str) -> dict | None:
    r = _get_redis()
    if r:
        try:
            data = r.get(f"icarus:pending_reply:{user_id}")
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logging.warning(f"[EMAIL] Redis get failed: {e}")
    return _pending_replies.get(user_id)


def clear_pending_reply(user_id: str):
    r = _get_redis()
    if r:
        try:
            r.delete(f"icarus:pending_reply:{user_id}")
            r.delete(f"icarus:edit_mode:{user_id}")
        except Exception as e:
            logging.warning(f"[EMAIL] Redis delete failed: {e}")
    _pending_replies.pop(user_id, None)
    _edit_mode.discard(user_id)


def set_edit_mode(user_id: str):
    r = _get_redis()
    if r:
        try:
            r.set(f"icarus:edit_mode:{user_id}", "1", ex=_TTL)
            return
        except Exception as e:
            logging.warning(f"[EMAIL] Redis set_edit_mode failed: {e}")
    _edit_mode.add(user_id)


def is_edit_mode(user_id: str) -> bool:
    r = _get_redis()
    if r:
        try:
            return bool(r.get(f"icarus:edit_mode:{user_id}"))
        except Exception as e:
            logging.warning(f"[EMAIL] Redis is_edit_mode failed: {e}")
    return user_id in _edit_mode


def update_pending_draft(user_id: str, new_draft: str):
    pending = get_pending_reply(user_id)
    if pending:
        pending["draft"] = new_draft
        r = _get_redis()
        if r:
            try:
                r.set(f"icarus:pending_reply:{user_id}", json.dumps(pending), ex=_TTL)
                r.delete(f"icarus:edit_mode:{user_id}")
            except Exception as e:
                logging.warning(f"[EMAIL] Redis update_draft failed: {e}")
                _pending_replies[user_id] = pending
                _edit_mode.discard(user_id)
        else:
            _pending_replies[user_id] = pending
            _edit_mode.discard(user_id)


def confirm_send_reply(user_id: str) -> str:
    pending = get_pending_reply(user_id)
    clear_pending_reply(user_id)
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
