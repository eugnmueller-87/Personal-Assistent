import os
import re
import base64
import asyncio
import logging
import requests
import anthropic
from datetime import datetime
from audit_log import log_event

_MAX_ATTEMPTS = 2
_fix_attempts: dict = {}

FORBIDDEN_AUTO_FIX_FILES = {
    "bot/auto_debug.py",
    "bot/claude_router.py",
    "bot/main.py",
    "bot/google_client.py",
    "bot/github_client.py",
    "bot/linkedin_client.py",
    "bot/skills/__init__.py",
}


def _notify(message: str):
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
    try:
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": message},
            timeout=10,
        )
    except Exception as e:
        logging.warning(f"[AUTO-DEBUG] Telegram notify failed: {e}")


def _get_file(path: str):
    repo = os.environ.get("RAILWAY_REPO", "")
    token = os.environ.get("GITHUB_TOKEN", "")
    if not repo:
        return None, None
    url = f"https://api.github.com/repos/{repo}/contents/{path}"
    r = requests.get(url, headers={"Authorization": f"token {token}"}, timeout=10)
    if r.status_code != 200:
        return None, None
    data = r.json()
    return base64.b64decode(data["content"]).decode("utf-8"), data["sha"]


def _create_pr(path: str, content: str, sha: str, summary: str) -> str | None:
    """Commits fix to a new branch and opens a PR. Returns PR URL or None."""
    repo = os.environ.get("RAILWAY_REPO", "")
    token = os.environ.get("GITHUB_TOKEN", "")
    if not repo or not token:
        return None
    headers = {"Authorization": f"token {token}"}
    base_url = f"https://api.github.com/repos/{repo}"

    r = requests.get(f"{base_url}/git/refs/heads/main", headers=headers, timeout=10)
    if r.status_code != 200:
        return None
    main_sha = r.json()["object"]["sha"]

    branch = f"auto-fix/{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"
    r = requests.post(
        f"{base_url}/git/refs",
        headers=headers,
        json={"ref": f"refs/heads/{branch}", "sha": main_sha},
        timeout=10,
    )
    if r.status_code not in (200, 201):
        return None

    r = requests.put(
        f"{base_url}/contents/{path}",
        headers=headers,
        json={
            "message": f"Auto-fix: {summary[:72]}",
            "content": base64.b64encode(content.encode()).decode(),
            "sha": sha,
            "branch": branch,
        },
        timeout=15,
    )
    if r.status_code not in (200, 201):
        return None

    r = requests.post(
        f"{base_url}/pulls",
        headers=headers,
        json={
            "title": f"Auto-fix: {summary[:72]}",
            "body": (
                f"Automated fix proposal for:\n\n```\n{summary}\n```\n\n"
                "**Review before merging.** Merging triggers a Railway redeploy."
            ),
            "head": branch,
            "base": "main",
        },
        timeout=10,
    )
    if r.status_code not in (200, 201):
        return None
    return r.json().get("html_url")


def _extract_file_path(tb_str: str) -> str | None:
    matches = re.findall(r'/bot/([^"]+\.py)', tb_str)
    if matches:
        return f"bot/{matches[-1]}"
    return None


def _ask_claude(tb_str: str, file_content: str, file_path: str) -> str:
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        messages=[{
            "role": "user",
            "content": (
                f"Fix this Python bot error. File: {file_path}\n\n"
                f"Error:\n{tb_str}\n\n"
                f"Current file:\n{file_content}\n\n"
                "Return ONLY the complete corrected Python source. "
                "No explanation, no markdown fences. Raw Python only."
            ),
        }]
    )
    raw = next((b.text for b in response.content if hasattr(b, "text")), "")
    raw = re.sub(r"^```python\n?", "", raw.strip())
    raw = re.sub(r"\n?```$", "", raw.strip())
    return raw.strip()


async def handle_error(exc: Exception, tb_str: str):
    error_summary = f"{type(exc).__name__}: {exc}"

    file_path = _extract_file_path(tb_str)
    if not file_path:
        _notify(f"ICARUS error (unknown file — manual fix needed):\n{error_summary}")
        log_event("error_unhandled", error_summary)
        return

    if file_path in FORBIDDEN_AUTO_FIX_FILES:
        _notify(f"ICARUS error in {file_path} (protected file — manual fix required):\n{error_summary}")
        log_event("auto_fix_blocked", f"{file_path}: {error_summary[:100]}")
        return

    attempts = _fix_attempts.get(file_path, 0)
    if attempts >= _MAX_ATTEMPTS:
        _notify(
            f"ICARUS: auto-fix exhausted for {file_path} ({_MAX_ATTEMPTS} attempts). "
            f"Manual fix needed.\n\n{error_summary}"
        )
        log_event("auto_fix_exhausted", f"{file_path}: {error_summary}")
        return
    _fix_attempts[file_path] = attempts + 1

    _notify(f"ICARUS error in {file_path}. Analyzing...\n\n{error_summary}")
    log_event("error_caught", f"{file_path}: {error_summary}")

    try:
        file_content, sha = await asyncio.to_thread(_get_file, file_path)
    except Exception as e:
        _notify(f"Auto-fix failed: couldn't read {file_path}: {e}")
        return

    if not file_content:
        repo = os.environ.get("RAILWAY_REPO", "unknown repo")
        _notify(f"Auto-fix failed: {file_path} not found in {repo}.")
        return

    try:
        fixed = await asyncio.to_thread(_ask_claude, tb_str, file_content, file_path)
    except Exception as e:
        _notify(f"Auto-fix failed: Claude error: {e}")
        return

    if not fixed or len(fixed) < 50:
        _notify(f"Auto-fix failed: Claude returned an empty result for {file_path}.")
        return

    try:
        pr_url = await asyncio.to_thread(_create_pr, file_path, fixed, sha, error_summary)
    except Exception as e:
        _notify(f"Auto-fix failed: PR creation error: {e}")
        return

    if not pr_url:
        _notify(f"Auto-fix failed: couldn't open PR for {file_path}.")
        return

    log_event("auto_fix_pr", f"{file_path}: {error_summary[:100]}")
    _notify(f"Fix PR ready for {file_path}. Review and merge to deploy:\n{pr_url}")
