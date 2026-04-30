from google_client import get_this_week_events, create_calendar_event

TOOLS = [
    {
        "name": "get_calendar",
        "description": "Get the user's calendar events for the next 7 days.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
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


def handle(name: str, inputs: dict, user_id: str = "default"):
    if name == "get_calendar":
        return get_this_week_events()
    if name == "create_calendar_event":
        return create_calendar_event(
            inputs["summary"],
            inputs["date"],
            inputs.get("start_time"),
            inputs.get("end_time"),
        )
    return None
