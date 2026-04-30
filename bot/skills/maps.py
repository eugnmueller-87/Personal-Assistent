from urllib.parse import quote_plus

TOOLS = [
    {
        "name": "get_maps_link",
        "description": (
            "Generate a Google Maps link for any location or directions request. "
            "Use when the user asks where something is, wants to find a place, "
            "or asks how to get from A to B. Always returns a clickable link."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Location to search, e.g. 'Parloa office Berlin' or 'sushi near Schwabing Munich'.",
                },
                "origin": {
                    "type": "string",
                    "description": "Starting point for directions. Omit for location searches.",
                },
                "destination": {
                    "type": "string",
                    "description": "End point for directions. Omit for location searches.",
                },
            },
            "required": [],
        },
    },
]


def handle(name: str, inputs: dict, user_id: str = "default"):
    if name == "get_maps_link":
        origin = inputs.get("origin", "").strip()
        destination = inputs.get("destination", "").strip()
        query = inputs.get("query", "").strip()

        if origin and destination:
            url = (
                f"https://www.google.com/maps/dir/?api=1"
                f"&origin={quote_plus(origin)}"
                f"&destination={quote_plus(destination)}"
            )
            return f"Directions from {origin} to {destination}:\n{url}"

        if query:
            url = f"https://www.google.com/maps/search/?api=1&query={quote_plus(query)}"
            return f"{query}:\n{url}"

        return "Please provide a location or origin/destination."
    return None
