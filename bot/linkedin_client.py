import os
import requests

_ACCESS_TOKEN = None
_pending_posts: dict = {}


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


def _publish(text: str) -> str:
    token = _get_token()
    author = f"urn:li:person:{_get_user_id()}"
    payload = {
        "author": author,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": text},
                "shareMediaCategory": "NONE",
            }
        },
        "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
    }
    resp = requests.post(
        "https://api.linkedin.com/v2/ugcPosts",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0",
        },
        json=payload,
        timeout=10,
    )
    resp.raise_for_status()
    return f"Posted. Post ID: {resp.headers.get('x-restli-id', 'unknown')}"


def stage_linkedin_post(user_id: str, text: str) -> str:
    _pending_posts[user_id] = text
    return f"LINKEDIN_STAGED:{text}"


def get_pending_post(user_id: str) -> str | None:
    return _pending_posts.get(user_id)


def clear_pending_post(user_id: str):
    _pending_posts.pop(user_id, None)


def confirm_post(user_id: str) -> str:
    text = _pending_posts.pop(user_id, None)
    if not text:
        return "No pending post found."
    return _publish(text)


def update_pending_post(user_id: str, text: str):
    _pending_posts[user_id] = text
