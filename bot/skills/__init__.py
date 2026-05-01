import logging
from . import calendar, email, github, search, maps, shopping, linkedin
from audit_log import log_event

_SKILLS = [calendar, email, github, search, maps, shopping, linkedin]


def get_all_tools() -> list:
    tools = []
    for skill in _SKILLS:
        tools.extend(skill.TOOLS)
    return tools


def _input_summary(inputs: dict) -> str:
    parts = []
    for k, v in inputs.items():
        v_str = str(v)
        parts.append(f"{k}={v_str[:40]!r}" if len(v_str) > 40 else f"{k}={v_str!r}")
    return ", ".join(parts)


def call_tool(name: str, inputs: dict, user_id: str = "default") -> str:
    for skill in _SKILLS:
        try:
            result = skill.handle(name, inputs, user_id)
            if result is not None:
                log_event("tool_call", f"user={user_id} tool={name} status=success input={_input_summary(inputs)}")
                return result
        except Exception as e:
            logging.error(f"[ICARUS] skill '{skill.__name__}' tool '{name}' failed: {e}")
            log_event("tool_call", f"user={user_id} tool={name} status=error err={str(e)[:80]}")
            return f"Tool unavailable ({name}): {e}"
    log_event("tool_call", f"user={user_id} tool={name} status=unknown")
    return f"Unknown tool: {name}"
