from maps_client import find_place, get_directions, maps_link, directions_link

TOOLS = [
    {
        "name": "find_place",
        "description": (
            "Find a place and get its address, rating, phone number, and opening hours. "
            "Use when the user asks where something is, wants to find a restaurant/shop/office, "
            "or asks if a place is open. Always returns a clickable Google Maps link."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Place to search, e.g. 'Parloa office Berlin' or 'sushi near Schwabing Munich'.",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_directions",
        "description": (
            "Get travel time and route between two locations. "
            "Use when the user asks how to get from A to B, how long it takes, or asks for directions. "
            "Always returns a clickable Google Maps link."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "origin": {
                    "type": "string",
                    "description": "Starting point, e.g. 'Munich Hauptbahnhof'.",
                },
                "destination": {
                    "type": "string",
                    "description": "End point, e.g. 'Berlin Hauptbahnhof'.",
                },
                "mode": {
                    "type": "string",
                    "description": "Travel mode: driving, transit, walking, bicycling. Default: transit.",
                },
            },
            "required": ["origin", "destination"],
        },
    },
]


def handle(name: str, inputs: dict, user_id: str = "default"):
    if name == "find_place":
        return find_place(inputs["query"])
    if name == "get_directions":
        return get_directions(
            inputs["origin"],
            inputs["destination"],
            inputs.get("mode", "transit"),
        )
    return None
