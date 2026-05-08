import os
import re
import imaplib
import smtplib
import email as _email_lib
from datetime import datetime, timedelta, timezone
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import decode_header as _decode_header
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

TIMEZONE = "Europe/Berlin"

GMAIL_USER = os.environ.get("GMAIL_USER", "eugnmueller@googlemail.com")
IMAP_HOST = "imap.gmail.com"
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587

SCOPES = [
    "https://www.googleapis.com/auth/calendar",
]


_creds = None
_REDIS_CREDS_KEY = "icarus:google:credentials"


def _redis_client():
    try:
        from upstash_redis import Redis
        url = os.environ["UPSTASH_REDIS_URL"]
        token = os.environ["UPSTASH_REDIS_TOKEN"]
        if "@" in token:
            token = token.split("@")[0]
        return Redis(url=url, token=token)
    except Exception:
        return None


def _save_creds(creds: Credentials):
    """Persist full credentials (access token + refresh token + expiry) to Redis."""
    import json
    r = _redis_client()
    if not r:
        return
    try:
        expiry_ts = None
        if creds.expiry:
            # Store as Unix timestamp to avoid naive/aware datetime confusion
            if creds.expiry.tzinfo is None:
                expiry_ts = creds.expiry.replace(tzinfo=timezone.utc).timestamp()
            else:
                expiry_ts = creds.expiry.timestamp()
        data = {
            "token": creds.token,
            "refresh_token": creds.refresh_token,
            "expiry_ts": expiry_ts,
        }
        r.set(_REDIS_CREDS_KEY, json.dumps(data))
    except Exception:
        pass


def _load_creds_from_redis() -> "Credentials | None":
    """Load credentials from Redis. Returns None if missing, expired, or invalid."""
    import json
    import time as _time
    r = _redis_client()
    if not r:
        return None
    try:
        raw = r.get(_REDIS_CREDS_KEY)
        if not raw:
            return None
        data = json.loads(raw)
        # Support both legacy "expiry" ISO string and new "expiry_ts" Unix timestamp
        expiry_ts = data.get("expiry_ts")
        if expiry_ts is None and data.get("expiry"):
            try:
                exp_str = data["expiry"].replace("Z", "+00:00")
                dt = datetime.fromisoformat(exp_str)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                expiry_ts = dt.timestamp()
            except Exception:
                expiry_ts = None
        now_ts = _time.time()
        # Only reuse if access token is valid for at least 5 more minutes
        if expiry_ts and expiry_ts > now_ts + 300:
            creds = Credentials(
                token=data["token"],
                refresh_token=data.get("refresh_token") or os.environ["GOOGLE_REFRESH_TOKEN"],
                token_uri="https://oauth2.googleapis.com/token",
                client_id=os.environ["GOOGLE_CLIENT_ID"],
                client_secret=os.environ["GOOGLE_CLIENT_SECRET"],
                scopes=SCOPES,
            )
            creds.expiry = datetime.fromtimestamp(expiry_ts, tz=timezone.utc).replace(tzinfo=None)
            return creds
        # Access token expired — return stub with refresh_token so caller can refresh
        if data.get("refresh_token"):
            return Credentials(
                token=None,
                refresh_token=data["refresh_token"],
                token_uri="https://oauth2.googleapis.com/token",
                client_id=os.environ["GOOGLE_CLIENT_ID"],
                client_secret=os.environ["GOOGLE_CLIENT_SECRET"],
                scopes=SCOPES,
            )
    except Exception:
        pass
    return None


def get_creds():
    global _creds
    if _creds is not None and _creds.valid:
        return _creds

    # Attempt to refresh if we have an in-memory expired cred
    if _creds is not None and _creds.refresh_token:
        try:
            _creds.refresh(Request())
            _save_creds(_creds)
            return _creds
        except Exception:
            _creds = None

    # Try restoring from Redis — fast path that avoids unnecessary refreshes on restart
    _creds = _load_creds_from_redis()
    if _creds is not None and _creds.valid:
        return _creds

    # Need to refresh — acquire a Redis lock so concurrent restarts don't race
    r = _redis_client()
    lock_key = "icarus:google:refresh_lock"
    lock_acquired = False
    if r:
        try:
            lock_acquired = bool(r.set(lock_key, "1", nx=True, ex=30))
        except Exception:
            pass

    if not lock_acquired and r:
        # Another instance is refreshing — wait briefly then retry from Redis
        import time as _t
        _t.sleep(3)
        _creds = _load_creds_from_redis()
        if _creds is not None and _creds.valid:
            return _creds

    try:
        if _creds is None:
            _creds = Credentials(
                token=None,
                refresh_token=os.environ["GOOGLE_REFRESH_TOKEN"],
                token_uri="https://oauth2.googleapis.com/token",
                client_id=os.environ["GOOGLE_CLIENT_ID"],
                client_secret=os.environ["GOOGLE_CLIENT_SECRET"],
                scopes=SCOPES,
            )
        _creds.refresh(Request())
        _save_creds(_creds)
        return _creds
    finally:
        if lock_acquired and r:
            try:
                r.delete(lock_key)
            except Exception:
                pass


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


def _imap_conn():
    """Open an authenticated IMAP connection."""
    password = os.environ["GMAIL_APP_PASSWORD"]
    conn = imaplib.IMAP4_SSL(IMAP_HOST)
    conn.login(GMAIL_USER, password)
    return conn


def _decode_str(value: str) -> str:
    parts = _decode_header(value)
    result = []
    for raw, charset in parts:
        if isinstance(raw, bytes):
            result.append(raw.decode(charset or "utf-8", errors="replace"))
        else:
            result.append(raw)
    return "".join(result)


def _extract_text_from_message(msg) -> str:
    """Extract plain text body from an email.Message object."""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                payload = part.get_payload(decode=True)
                if payload:
                    return payload.decode(part.get_content_charset() or "utf-8", errors="replace").strip()
        for part in msg.walk():
            if part.get_content_type() == "text/html":
                payload = part.get_payload(decode=True)
                if payload:
                    html = payload.decode(part.get_content_charset() or "utf-8", errors="replace")
                    return re.sub(r"<[^>]+>", " ", html).strip()
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            return payload.decode(msg.get_content_charset() or "utf-8", errors="replace").strip()
    return ""


def _fetch_envelope(conn, uid: bytes) -> dict:
    """Fetch From/Subject headers for a single UID."""
    _, data = conn.uid("fetch", uid, "(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT MESSAGE-ID REFERENCES)])")
    if not data or not data[0]:
        return {}
    raw = data[0][1] if isinstance(data[0], tuple) else data[0]
    msg = _email_lib.message_from_bytes(raw)
    return {
        "from": _decode_str(msg.get("From", "")),
        "subject": _decode_str(msg.get("Subject", "(no subject)")),
        "message_id": msg.get("Message-ID", ""),
        "references": msg.get("References", ""),
    }


_NOISE_SENDERS = (
    "noreply", "no-reply", "donotreply", "notifications", "mailer-daemon",
    "newsletter", "updates", "info@", "support@", "hello@", "team@",
)


def _is_noise(from_header: str) -> bool:
    low = from_header.lower()
    return any(p in low for p in _NOISE_SENDERS)


def get_recent_emails_with_ids(since_minutes=20):
    """Returns (formatted_text, set_of_uid_strings) for alert deduplication."""
    try:
        conn = _imap_conn()
    except Exception as e:
        raise RuntimeError(f"IMAP login failed: {e}") from e

    try:
        # Search Gmail Important folder — mirrors is:important filter
        try:
            conn.select('"[Gmail]/Important"')
        except Exception:
            conn.select("INBOX")
        since_dt = datetime.utcnow() - timedelta(minutes=since_minutes)
        since_str = since_dt.strftime("%d-%b-%Y")
        _, data = conn.uid("search", None, f'(UNSEEN SINCE "{since_str}")')
        uids = data[0].split() if data[0] else []
        if not uids:
            return None, set()

        uids = uids[-10:]  # fetch more, then filter noise
        results = []
        for uid in uids:
            env = _fetch_envelope(conn, uid)
            from_raw = env.get("from", "")
            if _is_noise(from_raw):
                continue
            sender = from_raw.split("<")[0].strip()
            subject = env.get("subject", "(no subject)")
            results.append((uid.decode(), sender, subject))

        if not results:
            return None, set()

        msg_ids = {uid for uid, _, _ in results}
        lines = [f"• {sender}: {subject}" for _, sender, subject in results[-5:]]
        return "\n".join(lines), msg_ids
    finally:
        try:
            conn.logout()
        except Exception:
            pass


def create_calendar_event(
    summary: str,
    date: str,
    start_time: str = None,
    end_time: str = None,
    recurrence: str = None,
    attendees: list = None,
    location: str = None,
    add_meet: bool = False,
    description: str = None,
) -> str:
    import uuid
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
        end_date = (datetime.fromisoformat(date) + timedelta(days=1)).strftime("%Y-%m-%d")
        event = {
            "summary": summary,
            "start": {"date": date},
            "end": {"date": end_date},
        }

    if description:
        event["description"] = description

    if recurrence:
        event["recurrence"] = [recurrence]

    if location:
        event["location"] = location

    if attendees:
        event["attendees"] = [{"email": e.strip()} for e in attendees]

    if add_meet:
        event["conferenceData"] = {
            "createRequest": {
                "requestId": str(uuid.uuid4()),
                "conferenceSolutionKey": {"type": "hangoutsMeet"},
            }
        }

    result = service.events().insert(
        calendarId="primary",
        body=event,
        conferenceDataVersion=1 if add_meet else 0,
        sendUpdates="all" if attendees else "none",
    ).execute()

    parts = [f"Created: {result.get('summary')} on {date}"]
    if recurrence:
        parts.append("(recurring)")
    if location:
        parts.append(f"Location: {location}")
    if attendees:
        parts.append(f"Invited: {', '.join(attendees)}")
    if add_meet:
        entry_points = result.get("conferenceData", {}).get("entryPoints", [])
        meet_link = next((ep["uri"] for ep in entry_points if ep.get("entryPointType") == "video"), "")
        if meet_link:
            parts.append(f"Meet: {meet_link}")
    return "\n".join(parts)


def delete_calendar_event(event_id: str) -> str:
    creds = get_creds()
    service = build("calendar", "v3", credentials=creds)
    service.events().delete(calendarId="primary", eventId=event_id).execute()
    return f"Deleted event {event_id}."


def find_calendar_events(query: str, date: str = None) -> str:
    creds = get_creds()
    service = build("calendar", "v3", credentials=creds)
    now = datetime.now(timezone.utc).isoformat()
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
    try:
        conn = _imap_conn()
    except Exception as e:
        raise RuntimeError(f"IMAP login failed: {e}") from e

    try:
        try:
            conn.select('"[Gmail]/Important"')
        except Exception:
            conn.select("INBOX")

        if since_minutes:
            since_dt = datetime.utcnow() - timedelta(minutes=since_minutes)
            label = f"last {since_minutes} min"
        else:
            since_dt = datetime.utcnow() - timedelta(days=3)
            label = "last 3 days"

        since_str = since_dt.strftime("%d-%b-%Y")
        _, data = conn.uid("search", None, f'(UNSEEN SINCE "{since_str}")')
        uids = data[0].split() if data[0] else []
        if not uids:
            return f"No unread important emails in the {label}."

        uids = uids[-max_results * 2:]  # fetch extra to account for noise filtering
        results = []
        for uid in uids:
            env = _fetch_envelope(conn, uid)
            from_raw = env.get("from", "")
            if _is_noise(from_raw):
                continue
            sender = from_raw.split("<")[0].strip()
            subject = env.get("subject", "(no subject)")
            results.append((uid.decode(), sender, subject))

        if not results:
            return f"No unread important emails in the {label}."

        results = results[-max_results:]
        lines = [f"• [ID:{uid}] {sender}: {subject}" for uid, sender, subject in results[-5:]]
        if len(results) > 5:
            lines.append(f"... and {len(results) - 5} more")
        return f"Unread important ({label}): {len(results)}\n" + "\n".join(lines)
    finally:
        try:
            conn.logout()
        except Exception:
            pass


def _gmail_query_to_imap(query: str) -> str:
    """Translate common Gmail query syntax to IMAP search criteria."""
    criteria = []
    folder = "INBOX"

    # Extract folder hints before building criteria
    if "in:sent" in query:
        folder = '"[Gmail]/Sent Mail"'
        query = query.replace("in:sent", "").strip()
    elif "in:anywhere" in query:
        folder = "ALL"
        query = query.replace("in:anywhere", "").strip()

    # from:name → FROM "name"
    for m in re.finditer(r'from:(\S+)', query):
        criteria.append(f'FROM "{m.group(1)}"')
    query = re.sub(r'from:\S+', '', query)

    # to:name → TO "name"
    for m in re.finditer(r'to:(\S+)', query):
        criteria.append(f'TO "{m.group(1)}"')
    query = re.sub(r'to:\S+', '', query)

    # subject:text → SUBJECT "text"
    for m in re.finditer(r'subject:(\S+)', query):
        criteria.append(f'SUBJECT "{m.group(1)}"')
    query = re.sub(r'subject:\S+', '', query)

    # newer_than:Nd → SINCE date
    m = re.search(r'newer_than:(\d+)d', query)
    if m:
        since_dt = datetime.utcnow() - timedelta(days=int(m.group(1)))
        criteria.append(f'SINCE "{since_dt.strftime("%d-%b-%Y")}"')
        query = re.sub(r'newer_than:\d+d', '', query)

    # Remaining words become TEXT search
    remainder = query.strip()
    if remainder:
        criteria.append(f'TEXT "{remainder}"')

    imap_criteria = " ".join(criteria) if criteria else "ALL"
    return folder, imap_criteria


def search_emails(query: str, max_results: int = 5) -> str:
    """Search emails using IMAP. Returns full body for single match, metadata list otherwise."""
    try:
        conn = _imap_conn()
    except Exception as e:
        raise RuntimeError(f"IMAP login failed: {e}") from e

    try:
        folder, criteria = _gmail_query_to_imap(query)
        if folder == "ALL":
            # Search all folders — try INBOX + Sent
            all_uids = []
            for f in ("INBOX", '"[Gmail]/Sent Mail"'):
                try:
                    conn.select(f, readonly=True)
                    _, data = conn.uid("search", None, criteria)
                    uids = data[0].split() if data[0] else []
                    all_uids.extend([(uid, f) for uid in uids])
                except Exception:
                    pass
        else:
            conn.select(folder, readonly=True)
            _, data = conn.uid("search", None, criteria)
            uids = data[0].split() if data[0] else []
            all_uids = [(uid, folder) for uid in uids]

        if not all_uids:
            return f"No emails found for: {query}"

        all_uids = all_uids[-max_results:]

        if len(all_uids) == 1:
            uid, f = all_uids[0]
            conn.select(f, readonly=True)
            return _get_body_by_uid(conn, uid)

        lines = []
        for uid, f in all_uids:
            try:
                conn.select(f, readonly=True)
                env = _fetch_envelope(conn, uid)
                sender = env.get("from", "").split("<")[0].strip()
                subject = env.get("subject", "(no subject)")
                lines.append(f"• [ID:{uid.decode()}] From: {sender} | {subject}")
            except Exception:
                pass
        return "\n".join(lines)
    finally:
        try:
            conn.logout()
        except Exception:
            pass


def _get_body_by_uid(conn, uid: bytes) -> str:
    """Fetch full body of a message by IMAP UID (conn must already be selected)."""
    _, data = conn.uid("fetch", uid, "(RFC822)")
    if not data or not data[0]:
        return "(could not fetch email)"
    raw = data[0][1] if isinstance(data[0], tuple) else data[0]
    msg = _email_lib.message_from_bytes(raw)
    sender = _decode_str(msg.get("From", "Unknown")).split("<")[0].strip()
    subject = _decode_str(msg.get("Subject", "(no subject)"))
    body = _extract_text_from_message(msg) or "(no body)"
    return f"From: {sender}\nSubject: {subject}\n\n{body}"


def get_email_body(message_id: str) -> str:
    """Fetch the full plain-text body of an email by IMAP UID."""
    try:
        conn = _imap_conn()
    except Exception as e:
        raise RuntimeError(f"IMAP login failed: {e}") from e

    try:
        # Try INBOX first, then Sent
        for folder in ("INBOX", '"[Gmail]/Sent Mail"', '"[Gmail]/All Mail"'):
            try:
                conn.select(folder, readonly=True)
                result = _get_body_by_uid(conn, message_id.encode())
                if result != "(could not fetch email)":
                    return result
            except Exception:
                continue
        return "(email not found)"
    finally:
        try:
            conn.logout()
        except Exception:
            pass


def get_email_details(message_id: str) -> dict:
    """Fetch headers needed to reply to an email by IMAP UID."""
    try:
        conn = _imap_conn()
    except Exception as e:
        raise RuntimeError(f"IMAP login failed: {e}") from e

    try:
        for folder in ("INBOX", '"[Gmail]/Sent Mail"', '"[Gmail]/All Mail"'):
            try:
                conn.select(folder, readonly=True)
                env = _fetch_envelope(conn, message_id.encode())
                if env:
                    from_raw = env.get("from", "")
                    match = re.search(r"<(.+?)>", from_raw)
                    sender_email = match.group(1) if match else from_raw
                    return {
                        "thread_id": None,  # not used in SMTP path
                        "to": sender_email,
                        "subject": env.get("subject", ""),
                        "message_id_header": env.get("message_id", ""),
                        "references": env.get("references", ""),
                    }
            except Exception:
                continue
        return {"thread_id": None, "to": "", "subject": "", "message_id_header": "", "references": ""}
    finally:
        try:
            conn.logout()
        except Exception:
            pass


def send_reply(thread_id, to: str, subject: str, in_reply_to: str, references: str, body: str) -> str:
    """Send a reply via SMTP using Gmail App Password."""
    password = os.environ["GMAIL_APP_PASSWORD"]
    reply_subject = subject if subject.lower().startswith("re:") else f"Re: {subject}"

    msg = MIMEMultipart()
    msg["From"] = GMAIL_USER
    msg["To"] = to
    msg["Subject"] = reply_subject
    if in_reply_to:
        msg["In-Reply-To"] = in_reply_to
        msg["References"] = f"{references} {in_reply_to}".strip() if references else in_reply_to
    msg.attach(MIMEText(body, "plain"))

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.ehlo()
        server.starttls()
        server.login(GMAIL_USER, password)
        server.sendmail(GMAIL_USER, to, msg.as_string())

    return f"Reply sent to {to}"
