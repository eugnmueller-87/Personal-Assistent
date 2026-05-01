import os
import json
import logging
from datetime import datetime, timezone

_REDIS_KEY = "icarus:audit_log"
_MAX_ENTRIES = 100


def _get_redis():
    try:
        url = os.environ.get("UPSTASH_REDIS_URL")
        token = os.environ.get("UPSTASH_REDIS_TOKEN")
        if url and token:
            from upstash_redis import Redis
            return Redis(url=url, token=token)
    except Exception:
        pass
    return None


def log_event(event_type: str, detail: str):
    r = _get_redis()
    if not r:
        return
    try:
        entry = json.dumps({
            "ts": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
            "type": event_type,
            "detail": detail[:200],
        })
        r.lpush(_REDIS_KEY, entry)
        r.ltrim(_REDIS_KEY, 0, _MAX_ENTRIES - 1)
    except Exception as e:
        logging.warning(f"[AUDIT] log_event failed: {e}")


def get_recent_events(n: int = 20) -> list[dict]:
    r = _get_redis()
    if not r:
        return []
    try:
        entries = r.lrange(_REDIS_KEY, 0, n - 1)
        return [json.loads(e) for e in entries]
    except Exception as e:
        logging.warning(f"[AUDIT] get_recent_events failed: {e}")
        return []
