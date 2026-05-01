from google_client import get_this_week_events, create_calendar_event, delete_calendar_event, find_calendar_events

TOOLS = [
    {
        "name": "get_calendar",
        "description": "Get the user's calendar events for the next 7 days.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "create_calendar_event",
        "description": (
            "Create an event on the user's Google Calendar. "
            "Supports one-time and recurring events, attendee invites, location, and Google Meet links. "
            "For recurring events, provide a recurrence rule in RRULE format, e.g. "
            "'RRULE:FREQ=WEEKLY;BYDAY=MO' for every Monday, "
            "'RRULE:FREQ=DAILY' for every day, "
            "'RRULE:FREQ=WEEKLY;COUNT=4' for 4 weeks. "
            "Set add_meet=true for remote/online meetings. "
            "Attendees will receive an email invitation automatically."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "summary": {"type": "string", "description": "Event title."},
                "date": {"type": "string", "description": "Start date in YYYY-MM-DD format."},
                "start_time": {"type": "string", "description": "Start time in HH:MM (24h). Omit for all-day events."},
                "end_time": {"type": "string", "description": "End time in HH:MM (24h). Defaults to 1 hour after start."},
                "recurrence": {"type": "string", "description": "RRULE string for recurring events, e.g. 'RRULE:FREQ=WEEKLY;BYDAY=MO'."},
                "attendees": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of attendee email addresses. Each will receive an invite.",
                },
                "location": {"type": "string", "description": "Physical address or room for in-person events."},
                "add_meet": {"type": "boolean", "description": "Set true to generate a Google Meet link for remote meetings."},
            },
            "required": ["summary", "date"],
        },
    },
    {
        "name": "find_calendar_events",
        "description": (
            "Search for calendar events by title or keyword. "
            "Returns event IDs needed for deletion or moving. "
            "Use before delete_calendar_event to find the event ID."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search term, e.g. event title or keyword."},
                "date": {"type": "string", "description": "Optional: filter by date in YYYY-MM-DD format."},
            },
            "required": ["query"],
        },
    },
    {
        "name": "delete_calendar_event",
        "description": (
            "Delete a calendar event by its ID. "
            "Use find_calendar_events first to get the event ID. "
            "To move an event: find it, delete it, then create a new one at the new time."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "event_id": {"type": "string", "description": "The event ID from find_calendar_events."},
            },
            "required": ["event_id"],
        },
    },
]


def handle(name: str, inputs: dict, user_id: str = "default"):
    if name == "get_calendar":
        return get_this_week_events()
    if name == "create_calendar_event":
        attendees = inputs.get("attendees")
        if isinstance(attendees, str):
            attendees = [e.strip() for e in attendees.split(",") if e.strip()]
        return create_calendar_event(
            inputs["summary"],
            inputs["date"],
            inputs.get("start_time"),
            inputs.get("end_time"),
            inputs.get("recurrence"),
            attendees,
            inputs.get("location"),
            inputs.get("add_meet", False),
        )
    if name == "find_calendar_events":
        return find_calendar_events(inputs["query"], inputs.get("date"))
    if name == "delete_calendar_event":
        return delete_calendar_event(inputs["event_id"])
    return None
