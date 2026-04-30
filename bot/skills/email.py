import logging
from google_client import get_unread_emails, search_emails, get_email_details, send_reply

_pending_replies: dict = {}
_edit_mode: set = set()

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


def handle(name: str, inputs: dict, user_id: str = "default"):
    if name == "get_emails":
        return get_unread_emails(inputs.get("max_results", 10), inputs.get("since_minutes"))
    if name == "search_emails":
        return search_emails(inputs["query"], inputs.get("max_results", 5))
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
    return None


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
