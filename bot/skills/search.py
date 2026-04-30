from tavily_client import web_search

TOOLS = [
    {
        "name": "web_search",
        "description": (
            "Search the live web for current information. "
            "Use when the user asks about news, weather, prices, exchange rates, "
            "company info, people, current events, or anything requiring up-to-date data. "
            "Do NOT use for calendar, email, tasks, or roadmap — use those dedicated tools instead."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Specific search query.",
                },
            },
            "required": ["query"],
        },
    },
]


def handle(name: str, inputs: dict, user_id: str = "default"):
    if name == "web_search":
        return web_search(inputs["query"])
    return None
