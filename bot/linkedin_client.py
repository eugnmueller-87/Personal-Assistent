import os
import re
import logging
import requests
from redis_ns import NS

_ACCESS_TOKEN = None
_pending_posts: dict = {}
_TTL = 86400  # 24h — pending approvals expire if not acted on

# Add LinkedIn URNs for people or companies you mention frequently.
# Format: lowercase name → LinkedIn URN
# To find a URN: go to their LinkedIn page, view page source and search for
# "organizationUrn" or "fsd_company". The numeric ID appears in the URL.
KNOWN_MENTIONS: dict = {
    "ironhack": "urn:li:organization:3297892",
}


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


def _get_token() -> str:
    global _ACCESS_TOKEN
    if _ACCESS_TOKEN is None:
        _ACCESS_TOKEN = os.environ["LINKEDIN_ACCESS_TOKEN"]
    return _ACCESS_TOKEN


def _get_user_id() -> str:
    resp = requests.get(
        "https://api.linkedin.com/v2/userinfo",
        headers={"Authorization": f"Bearer {_get_token()}"},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()["sub"]


def _apply_mentions(text: str) -> str:
    """Convert @Name to LTF mention syntax for known entities."""
    def replace(m):
        name = m.group(1)
        urn = KNOWN_MENTIONS.get(name.lower())
        if urn:
            return f"@[{name}]({urn})"
        return m.group(0)
    return re.sub(r"@(\w+)", replace, text)


def _publish(text: str) -> str:
    token = _get_token()
    author = f"urn:li:person:{_get_user_id()}"
    commentary = _apply_mentions(text)
    payload = {
        "author": author,
        "commentary": commentary,
        "visibility": "PUBLIC",
        "distribution": {"feedDistribution": "MAIN_FEED"},
        "lifecycleState": "PUBLISHED",
    }
    resp = requests.post(
        "https://api.linkedin.com/rest/posts",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "LinkedIn-Version": "202502",
            "X-Restli-Protocol-Version": "2.0.0",
        },
        json=payload,
        timeout=10,
    )
    resp.raise_for_status()
    return f"Posted. Post ID: {resp.headers.get('x-restli-id', 'unknown')}"


def stage_linkedin_post(user_id: str, text: str) -> str:
    r = _get_redis()
    if r:
        try:
            r.set(f"{NS}:pending_post:{user_id}", text, ex=_TTL)
        except Exception as e:
            logging.warning(f"[LINKEDIN] Redis stage failed: {e}")
            _pending_posts[user_id] = text
    else:
        _pending_posts[user_id] = text
    return f"LINKEDIN_STAGED:{text}"


def get_pending_post(user_id: str) -> str | None:
    r = _get_redis()
    if r:
        try:
            return r.get(f"{NS}:pending_post:{user_id}")
        except Exception as e:
            logging.warning(f"[LINKEDIN] Redis get failed: {e}")
    return _pending_posts.get(user_id)


def clear_pending_post(user_id: str):
    r = _get_redis()
    if r:
        try:
            r.delete(f"{NS}:pending_post:{user_id}")
        except Exception as e:
            logging.warning(f"[LINKEDIN] Redis delete failed: {e}")
    _pending_posts.pop(user_id, None)


def confirm_post(user_id: str) -> str:
    text = get_pending_post(user_id)
    clear_pending_post(user_id)
    if not text:
        return "No pending post found."
    return _publish(text)


def update_pending_post(user_id: str, text: str):
    r = _get_redis()
    if r:
        try:
            r.set(f"{NS}:pending_post:{user_id}", text, ex=_TTL)
        except Exception as e:
            logging.warning(f"[LINKEDIN] Redis update failed: {e}")
            _pending_posts[user_id] = text
    else:
        _pending_posts[user_id] = text
