import os
import re
import base64
import time
from datetime import datetime, timedelta, timezone
from email.mime.text import MIMEText
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

TIMEZONE = "Europe/Berlin"


SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/gmail.modify",
]


def get_creds():
    creds = Credentials(
        token=None,
        refresh_token=os.environ["GOOGLE_REFRESH_TOKEN"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.environ["GOOGLE_CLIENT_ID"],
        client_secret=os.environ["GOOGLE_CLIENT_SECRET"],
        scopes=SCOPES,
    )
    creds.refresh(Request())
    return creds


def get_today_events():
    creds = get_creds()
    service = build("calendar", "v3", credentials=creds)

    from zoneinfo import ZoneInfo
    berlin = ZoneInfo(TIMEZONE)
    now_berlin = datetime.now(berlin)
    start = now_berlin.replace(hour=0, minute=0, second=0, microsecond=0).astimezone(timezone.utc)
    end = start + timedelta(days=1)

    result = service.events().list(
        calendarId="primary",
        timeMin=start.isoformat(),
        timeMax=end.isoformat(),
        singleEvents=True,
        orderBy="startTime",
    ).execute()

    events = result.get("items", [])
    if not events:
        return "Nothing on the calendar today."

    lines = []
    for e in events:
        start_raw = e["start"].get("dateTime", e["start"].get("date", ""))
        if "T" in start_raw:
            dt = datetime.fromisoformat(start_raw)
            time_str = dt.strftime("%H:%M")
        else:
            time_str = "All day"
        lines.append(f"• {time_str} — {e.get('summary', '(no title)')}")

    return "\n".join(lines)


def get_this_week_events():
    creds = get_creds()
    service = build("calendar", "v3", credentials=creds)

    now = datetime.now(timezone.utc)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=7)

    result = service.events().list(
        calendarId="primary",
        timeMin=start.isoformat(),
        timeMax=end.isoformat(),
        singleEvents=True,
        orderBy="startTime",
    ).execute()

    events = result.get("items", [])
    if not events:
        return "No events this week."

    lines = []
    for e in events:
        start_raw = e["start"].get("dateTime", e["start"].get("date", ""))
        if "T" in start_raw:
            dt = datetime.fromisoformat(start_raw)
            time_str = dt.strftime("%a %d %b %H:%M")
        else:
            dt = datetime.fromisoformat(start_raw)
            time_str = dt.strftime("%a %d %b")
        lines.append(f"• {time_str} — {e.get('summary', '(no title)')}")

    return "\n".join(lines)


def get_recent_emails_with_ids(since_minutes=20):
    """Returns (formatted_text, set_of_message_ids) for alert deduplication."""
    creds = get_creds()
    service = build("gmail", "v1", credentials=creds)

    since_ts = int(time.time()) - (since_minutes * 60)
    q = (
        f"is:unread is:important after:{since_ts} "
        "-category:promotions -category:social -category:updates "
        "-category:forums -from:noreply -from:no-reply -from:donotreply -from:notifications"
    )

    result = service.users().messages().list(userId="me", q=q, maxResults=5).execute()
    messages = result.get("messages", [])

    if not messages:
        return None, set()

    msg_ids = {m["id"] for m in messages}
    lines = []
    for msg in messages:
        detail = service.users().messages().get(
            userId="me", id=msg["id"], format="metadata",
            metadataHeaders=["From", "Subject"],
        ).execute()
        headers = {h["name"]: h["value"] for h in detail["payload"]["headers"]}
        sender = headers.get("From", "Unknown").split("<")[0].strip()
        subject = headers.get("Subject", "(no subject)")
        lines.append(f"• {sender}: {subject}")

    return "\n".join(lines), msg_ids


def create_calendar_event(
    summary: str,
    date: str,
    start_time: str = None,
    end_time: str = None,
    recurrence: str = None,
) -> str:
    creds = get_creds()
    service = build("calendar", "v3", credentials=creds)

    if start_time:
        if not end_time:
            st = datetime.strptime(f"{date}T{start_time}", "%Y-%m-%dT%H:%M")
            end_time = (st + timedelta(hours=1)).strftime("%H:%M")
        event = {
            "summary": summary,
            "start": {"dateTime": f"{date}T{start_time}:00", "timeZone": TIMEZONE},
            "end": {"dateTime": f"{date}T{end_time}:00", "timeZone": TIMEZONE},
        }
    else:
        event = {
            "summary": summary,
            "start": {"date": date},
            "end": {"date": date},
        }

    if recurrence:
        event["recurrence"] = [recurrence]

    result = service.events().insert(calendarId="primary", body=event).execute()
    return f"Created: {result.get('summary')} on {date}" + (f" (recurring)" if recurrence else "")


def delete_calendar_event(event_id: str) -> str:
    creds = get_creds()
    service = build("calendar", "v3", credentials=creds)
    service.events().delete(calendarId="primary", eventId=event_id).execute()
    return f"Deleted event {event_id}."


def find_calendar_events(query: str, date: str = None) -> str:
    creds = get_creds()
    service = build("calendar", "v3", credentials=creds)
    now = datetime.utcnow().isoformat() + "Z"
    params = {
        "calendarId": "primary",
        "q": query,
        "timeMin": now,
        "maxResults": 10,
        "singleEvents": True,
        "orderBy": "startTime",
    }
    if date:
        params["timeMin"] = f"{date}T00:00:00Z"
        params["timeMax"] = f"{date}T23:59:59Z"
    result = service.events().list(**params).execute()
    events = result.get("items", [])
    if not events:
        return "No matching events found."
    lines = []
    for e in events:
        start = e["start"].get("dateTime", e["start"].get("date", ""))
        lines.append(f"[ID:{e['id']}] {e.get('summary','(no title)')} — {start}")
    return "\n".join(lines)


def get_unread_emails(max_results=10, since_minutes=None):
    creds = get_creds()
    service = build("gmail", "v1", credentials=creds)

    base = (
        "is:unread is:important "
        "-category:promotions -category:social -category:updates "
        "-category:forums -from:noreply -from:no-reply -from:donotreply -from:notifications"
    )

    if since_minutes:
        since_ts = int(time.time()) - (since_minutes * 60)
        q = f"{base} after:{since_ts}"
    else:
        q = f"{base} newer_than:3d"

    result = service.users().messages().list(
        userId="me",
        q=q,
        maxResults=max_results,
    ).execute()

    messages = result.get("messages", [])
    if not messages:
        label = f"last {since_minutes} minutes" if since_minutes else "last 3 days"
        return f"No unread important emails in the {label}."

    lines = []
    for msg in messages[:5]:
        detail = service.users().messages().get(
            userId="me", id=msg["id"], format="metadata",
            metadataHeaders=["From", "Subject"],
        ).execute()
        headers = {h["name"]: h["value"] for h in detail["payload"]["headers"]}
        sender = headers.get("From", "Unknown").split("<")[0].strip()
        subject = headers.get("Subject", "(no subject)")
        lines.append(f"• [ID:{msg['id']}] {sender}: {subject}")

    if len(messages) > 5:
        lines.append(f"... and {len(messages) - 5} more")

    label = f"last {since_minutes} min" if since_minutes else "last 3 days"
    return f"Unread important ({label}): {len(messages)}\n" + "\n".join(lines)


def search_emails(query: str, max_results: int = 5) -> str:
    """Search emails. Returns full body when result is a single email, metadata list otherwise."""
    creds = get_creds()
    service = build("gmail", "v1", credentials=creds)

    result = service.users().messages().list(
        userId="me", q=query, maxResults=max_results,
    ).execute()
    messages = result.get("messages", [])

    if not messages:
        return f"No emails found for query: {query}"

    if len(messages) == 1:
        return get_email_body(messages[0]["id"])

    lines = []
    for msg in messages:
        detail = service.users().messages().get(
            userId="me", id=msg["id"], format="metadata",
            metadataHeaders=["From", "To", "Subject", "Date"],
        ).execute()
        headers = {h["name"]: h["value"] for h in detail["payload"]["headers"]}
        sender = headers.get("From", "").split("<")[0].strip()
        subject = headers.get("Subject", "(no subject)")
        date = headers.get("Date", "")[:16]
        lines.append(f"• [ID:{msg['id']}] {date} | From: {sender} | {subject}")

    return "\n".join(lines)


def _extract_plain_text(payload: dict) -> str:
    mime = payload.get("mimeType", "")
    if mime == "text/plain":
        data = payload.get("body", {}).get("data", "")
        if data:
            return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace").strip()
    for part in payload.get("parts", []):
        text = _extract_plain_text(part)
        if text:
            return text
    if mime == "text/html":
        data = payload.get("body", {}).get("data", "")
        if data:
            html = base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
            return re.sub(r"<[^>]+>", " ", html).strip()
    return ""


def get_email_body(message_id: str) -> str:
    """Fetch the full plain-text body of an email by message ID."""
    creds = get_creds()
    service = build("gmail", "v1", credentials=creds)

    detail = service.users().messages().get(
        userId="me", id=message_id, format="full",
    ).execute()

    headers = {h["name"]: h["value"] for h in detail["payload"]["headers"]}
    sender = headers.get("From", "Unknown").split("<")[0].strip()
    subject = headers.get("Subject", "(no subject)")
    body = _extract_plain_text(detail["payload"]) or "(no body)"

    return f"From: {sender}\nSubject: {subject}\n\n{body}"


def get_email_details(message_id: str) -> dict:
    creds = get_creds()
    service = build("gmail", "v1", credentials=creds)

    detail = service.users().messages().get(
        userId="me", id=message_id, format="metadata",
        metadataHeaders=["From", "Subject", "Message-ID", "References"],
    ).execute()

    headers = {h["name"]: h["value"] for h in detail["payload"]["headers"]}
    from_raw = headers.get("From", "")
    match = re.search(r"<(.+?)>", from_raw)
    sender_email = match.group(1) if match else from_raw

    return {
        "thread_id": detail["threadId"],
        "to": sender_email,
        "subject": headers.get("Subject", ""),
        "message_id_header": headers.get("Message-ID", ""),
        "references": headers.get("References", ""),
    }


def send_reply(thread_id: str, to: str, subject: str, in_reply_to: str, references: str, body: str) -> str:
    creds = get_creds()
    service = build("gmail", "v1", credentials=creds)

    reply_subject = subject if subject.lower().startswith("re:") else f"Re: {subject}"
    msg = MIMEText(body)
    msg["To"] = to
    msg["Subject"] = reply_subject
    msg["In-Reply-To"] = in_reply_to
    msg["References"] = f"{references} {in_reply_to}".strip()

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    sent = service.users().messages().send(
        userId="me",
        body={"raw": raw, "threadId": thread_id},
    ).execute()
    return f"Reply sent to {to} (id: {sent['id']})"
