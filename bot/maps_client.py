import os
import requests
from urllib.parse import quote_plus

MAPS_API_KEY = None


def _key():
    global MAPS_API_KEY
    if not MAPS_API_KEY:
        MAPS_API_KEY = os.environ["GOOGLE_MAPS_API_KEY"]
    return MAPS_API_KEY


def maps_link(query: str) -> str:
    return f"https://www.google.com/maps/search/?api=1&query={quote_plus(query)}"


def directions_link(origin: str, destination: str) -> str:
    return (
        f"https://www.google.com/maps/dir/?api=1"
        f"&origin={quote_plus(origin)}"
        f"&destination={quote_plus(destination)}"
    )


def find_place(query: str) -> str:
    resp = requests.get(
        "https://maps.googleapis.com/maps/api/place/findplacefromtext/json",
        params={
            "input": query,
            "inputtype": "textquery",
            "fields": "name,formatted_address,opening_hours,rating,formatted_phone_number,place_id",
            "key": _key(),
        },
        timeout=10,
    )
    resp.raise_for_status()
    candidates = resp.json().get("candidates", [])
    if not candidates:
        return f"No place found for '{query}'.\n{maps_link(query)}"

    p = candidates[0]
    name = p.get("name", query)
    address = p.get("formatted_address", "")
    rating = p.get("rating", "")
    phone = p.get("formatted_phone_number", "")
    hours = p.get("opening_hours", {})
    open_now = hours.get("open_now")

    lines = [name]
    if address:
        lines.append(address)
    if rating:
        lines.append(f"Rating: {rating}/5")
    if phone:
        lines.append(f"Phone: {phone}")
    if open_now is True:
        lines.append("Open now")
    elif open_now is False:
        lines.append("Currently closed")
    lines.append(maps_link(query))

    return "\n".join(lines)


def get_directions(origin: str, destination: str, mode: str = "transit") -> str:
    resp = requests.get(
        "https://maps.googleapis.com/maps/api/directions/json",
        params={
            "origin": origin,
            "destination": destination,
            "mode": mode,
            "key": _key(),
        },
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    routes = data.get("routes", [])
    if not routes:
        return f"No route found.\n{directions_link(origin, destination)}"

    leg = routes[0]["legs"][0]
    duration = leg["duration"]["text"]
    distance = leg["distance"]["text"]
    summary = routes[0].get("summary", "")

    lines = [f"{origin} → {destination}"]
    lines.append(f"{duration} ({distance})")
    if summary:
        lines.append(f"Via {summary}")
    lines.append(directions_link(origin, destination))

    return "\n".join(lines)
