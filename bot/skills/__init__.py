import logging
from . import calendar, email, github, search, maps, shopping

_SKILLS = [calendar, email, github, search, maps, shopping]


def get_all_tools() -> list:
    tools = []
    for skill in _SKILLS:
        tools.extend(skill.TOOLS)
    return tools


def call_tool(name: str, inputs: dict, user_id: str = "default") -> str:
    for skill in _SKILLS:
        try:
            result = skill.handle(name, inputs, user_id)
            if result is not None:
                return result
        except Exception as e:
            logging.error(f"[ICARUS] skill '{skill.__name__}' tool '{name}' failed: {e}")
            return f"Tool unavailable ({name}): {e}"
    return f"Unknown tool: {name}"
