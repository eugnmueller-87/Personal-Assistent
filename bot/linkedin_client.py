import os
import requests

_ACCESS_TOKEN = None


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


def post_to_linkedin(text: str) -> str:
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
    post_id = resp.headers.get("x-restli-id", "unknown")
    return f"Posted successfully. Post ID: {post_id}"
