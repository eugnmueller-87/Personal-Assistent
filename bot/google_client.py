import os
import re
import imaplib
import smtplib
import email as _email_lib
from datetime import datetime, timedelta, timezone
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import decode_header as _decode_header

TIMEZONE = "Europe/Berlin"
CALDAV_URL = "https://www.google.com/calendar/dav/eugnmueller@googlemail.com/events/"

GMAIL_USER = os.environ.get("GMAIL_USER", "eugnmueller@googlemail.com")
IMAP_HOST = "imap.gmail.com"
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587


def _caldav_client():
    import caldav
    password = os.environ["GMAIL_APP_PASSWORD"]
    client = caldav.DAVClient(url=CALDAV_URL, username=GMAIL_USER, password=password)
    return client.calendar(url=CALDAV_URL)


def _get_vevent(cal_result):
    """Extract the VEVENT component from a caldav result object."""
    vi = cal_result.vobject_instance
    # vobject_instance is a VCALENDAR — find the VEVENT inside it
    vevent = getattr(vi, "vevent", None)
    if vevent is None:
        # Try iterating contents for VEVENT
        for component in getattr(vi, "contents", {}).get("vevent", []):
            return component
    return vevent


def _parse_event(vevent) -> dict:
    """Extract summary, start, end from a vobject vevent component."""
    summary = str(getattr(vevent, "summary", None) and vevent.summary.value or "(no title)")
    dtstart = vevent.dtstart.value
    dtend = getattr(vevent, "dtend", None)
    dtend = dtend.value if dtend else dtstart
    if isinstance(dtstart, datetime):
        if dtstart.tzinfo is None:
            from zoneinfo import ZoneInfo
            dtstart = dtstart.replace(tzinfo=ZoneInfo(TIMEZONE))
        if isinstance(dtend, datetime) and dtend.tzinfo is None:
            from zoneinfo import ZoneInfo
            dtend = dtend.replace(tzinfo=ZoneInfo(TIMEZONE))
    uid = str(getattr(vevent, "uid", None) and vevent.uid.value or "")
    return {"summary": summary, "start": dtstart, "end": dtend, "uid": uid}


def get_today_events():
    from zoneinfo import ZoneInfo
    berlin = ZoneInfo(TIMEZONE)
    now_berlin = datetime.now(berlin)
    start = now_berlin.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)

    cal = _caldav_client()
    results = cal.date_search(start=start, end=end, expand=True)

    if not results:
        return "Nothing on the calendar today."

    events = []
    for r in results:
        ve = _get_vevent(r)
        if ve is None:
            continue
        events.append(_parse_event(ve))
    events.sort(key=lambda e: e["start"] if isinstance(e["start"], datetime) else datetime.combine(e["start"], datetime.min.time()))

    lines = []
    for e in events:
        if isinstance(e["start"], datetime):
            time_str = e["start"].strftime("%H:%M")
        else:
            time_str = "All day"
        lines.append(f"• {time_str} — {e['summary']}")
    return "\n".join(lines)


def get_this_week_events():
    from zoneinfo import ZoneInfo
    berlin = ZoneInfo(TIMEZONE)
    now_berlin = datetime.now(berlin)
    start = now_berlin.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=7)

    cal = _caldav_client()
    results = cal.date_search(start=start, end=end, expand=True)

    if not results:
        return "No events this week."

    events = []
    for r in results:
        ve = _get_vevent(r)
        if ve is None:
            continue
        events.append(_parse_event(ve))
    events.sort(key=lambda e: e["start"] if isinstance(e["start"], datetime) else datetime.combine(e["start"], datetime.min.time()))

    lines = []
    for e in events:
        if isinstance(e["start"], datetime):
            time_str = e["start"].strftime("%a %d %b %H:%M")
        else:
            time_str = datetime.combine(e["start"], datetime.min.time()).strftime("%a %d %b")
        lines.append(f"• {time_str} — {e['summary']}")
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
        for folder in ('"[Gmail]/Important"', "[Gmail]/Important", "INBOX"):
            status, _ = conn.select(folder)
            if status == "OK":
                break
        else:
            return None, set()
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
    from zoneinfo import ZoneInfo
    berlin = ZoneInfo(TIMEZONE)

    if start_time:
        if not end_time:
            st = datetime.strptime(f"{date}T{start_time}", "%Y-%m-%dT%H:%M")
            end_time = (st + timedelta(hours=1)).strftime("%H:%M")
        dt_start = datetime.strptime(f"{date}T{start_time}", "%Y-%m-%dT%H:%M").replace(tzinfo=berlin)
        dt_end = datetime.strptime(f"{date}T{end_time}", "%Y-%m-%dT%H:%M").replace(tzinfo=berlin)
        all_day = False
    else:
        dt_start = datetime.strptime(date, "%Y-%m-%d").date()
        dt_end = (datetime.strptime(date, "%Y-%m-%d") + timedelta(days=1)).date()
        all_day = True

    uid = str(uuid.uuid4())
    if all_day:
        ical = (
            "BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//ICARUS//EN\r\n"
            "BEGIN:VEVENT\r\n"
            f"UID:{uid}\r\n"
            f"SUMMARY:{summary}\r\n"
            f"DTSTART;VALUE=DATE:{dt_start.strftime('%Y%m%d')}\r\n"
            f"DTEND;VALUE=DATE:{dt_end.strftime('%Y%m%d')}\r\n"
        )
    else:
        ical = (
            "BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//ICARUS//EN\r\n"
            "BEGIN:VEVENT\r\n"
            f"UID:{uid}\r\n"
            f"SUMMARY:{summary}\r\n"
            f"DTSTART;TZID={TIMEZONE}:{dt_start.strftime('%Y%m%dT%H%M%S')}\r\n"
            f"DTEND;TZID={TIMEZONE}:{dt_end.strftime('%Y%m%dT%H%M%S')}\r\n"
        )
    if description:
        ical += f"DESCRIPTION:{description}\r\n"
    if location:
        ical += f"LOCATION:{location}\r\n"
    if recurrence:
        ical += f"{recurrence}\r\n"
    if attendees:
        for a in attendees:
            ical += f"ATTENDEE:mailto:{a.strip()}\r\n"
    ical += "END:VEVENT\r\nEND:VCALENDAR\r\n"

    cal = _caldav_client()
    cal.save_event(ical)

    parts = [f"Created: {summary} on {date}"]
    if recurrence:
        parts.append("(recurring)")
    if location:
        parts.append(f"Location: {location}")
    if attendees:
        parts.append(f"Invited: {', '.join(attendees)}")
    if add_meet:
        parts.append("Note: Google Meet links require the Calendar API — not supported via CalDAV.")
    return "\n".join(parts)


def delete_calendar_event(event_id: str) -> str:
    cal = _caldav_client()
    results = cal.date_search(
        start=datetime.now(timezone.utc) - timedelta(days=365),
        end=datetime.now(timezone.utc) + timedelta(days=365),
        expand=True,
    )
    for r in results:
        ve = _get_vevent(r)
        if ve is None:
            continue
        uid = str(getattr(ve, "uid", None) and ve.uid.value or "")
        if uid == event_id or event_id in str(r.url):
            r.delete()
            return f"Deleted event {event_id}."
    return f"Event {event_id} not found."


def find_calendar_events(query: str, date: str = None) -> str:
    from zoneinfo import ZoneInfo
    berlin = ZoneInfo(TIMEZONE)
    if date:
        start = datetime.strptime(date, "%Y-%m-%d").replace(tzinfo=berlin)
        end = start + timedelta(days=1)
    else:
        start = datetime.now(berlin)
        end = start + timedelta(days=30)

    cal = _caldav_client()
    results = cal.date_search(start=start, end=end, expand=True)
    query_lower = query.lower()
    matches = []
    for r in results:
        ve = _get_vevent(r)
        if ve is None:
            continue
        e = _parse_event(ve)
        if query_lower in e["summary"].lower():
            matches.append(e)
    if not matches:
        return "No matching events found."
    lines = []
    for e in matches:
        time_str = e["start"].strftime("%Y-%m-%d %H:%M") if isinstance(e["start"], datetime) else str(e["start"])
        lines.append(f"[ID:{e['uid']}] {e['summary']} — {time_str}")
    return "\n".join(lines)


def get_unread_emails(max_results=10, since_minutes=None):
    try:
        conn = _imap_conn()
    except Exception as e:
        raise RuntimeError(f"IMAP login failed: {e}") from e

    try:
        for folder in ('"[Gmail]/Important"', "[Gmail]/Important", "INBOX"):
            status, _ = conn.select(folder)
            if status == "OK":
                break
        else:
            return "Could not select mailbox."

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
        folder = "[Gmail]/Sent Mail"
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
            for f in ("INBOX", "[Gmail]/Sent Mail"):
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
        for folder in ("INBOX", "[Gmail]/Sent Mail", "[Gmail]/All Mail"):
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
        for folder in ("INBOX", "[Gmail]/Sent Mail", "[Gmail]/All Mail"):
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
