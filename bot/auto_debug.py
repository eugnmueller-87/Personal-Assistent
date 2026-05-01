import os
import re
import base64
import asyncio
import logging
import requests
import anthropic

RAILWAY_REPO = os.environ.get("RAILWAY_REPO", "eugnmueller-87/Personal-Assistent")
_REDIS_KEY = "icarus:pending_fix"
_MAX_ATTEMPTS = 2
_fix_attempts: dict = {}


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


def _get_file(path: str):
    token = os.environ.get("GITHUB_TOKEN", "")
    url = f"https://api.github.com/repos/{RAILWAY_REPO}/contents/{path}"
    r = requests.get(url, headers={"Authorization": f"token {token}"}, timeout=10)
    if r.status_code != 200:
        return None, None
    data = r.json()
    return base64.b64decode(data["content"]).decode("utf-8"), data["sha"]


def _commit_fix(path: str, content: str, sha: str, summary: str) -> bool:
    token = os.environ.get("GITHUB_TOKEN", "")
    url = f"https://api.github.com/repos/{RAILWAY_REPO}/contents/{path}"
    body = {
        "message": f"Auto-fix: {summary[:72]}",
        "content": base64.b64encode(content.encode()).decode(),
        "sha": sha,
    }
    r = requests.put(url, json=body, headers={"Authorization": f"token {token}"}, timeout=15)
    return r.status_code in (200, 201)


def _extract_file_path(tb_str: str) -> str | None:
    # Match paths like /app/bot/claude_router.py or /app/bot/skills/email.py
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
        return

    attempts = _fix_attempts.get(file_path, 0)
    if attempts >= _MAX_ATTEMPTS:
        _notify(
            f"ICARUS: auto-fix exhausted for {file_path} ({_MAX_ATTEMPTS} attempts). "
            f"Manual fix needed.\n\n{error_summary}"
        )
        return
    _fix_attempts[file_path] = attempts + 1

    _notify(f"ICARUS error in {file_path}. Analyzing and fixing...\n\n{error_summary}")

    try:
        file_content, sha = await asyncio.to_thread(_get_file, file_path)
    except Exception as e:
        _notify(f"Auto-fix failed: couldn't read {file_path}: {e}")
        return

    if not file_content:
        _notify(f"Auto-fix failed: {file_path} not found in {RAILWAY_REPO}.")
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
        committed = await asyncio.to_thread(_commit_fix, file_path, fixed, sha, error_summary)
    except Exception as e:
        _notify(f"Auto-fix failed: GitHub commit error: {e}")
        return

    if not committed:
        _notify(f"Auto-fix failed: couldn't push to {RAILWAY_REPO}/{file_path}.")
        return

    r = _get_redis()
    if r:
        try:
            r.set(_REDIS_KEY, f"{file_path}: {error_summary[:120]}", ex=600)
        except Exception:
            pass

    _notify(f"Fix committed to {file_path}. Railway redeploying (~90s).")


async def check_pending_fix(bot, chat_id: str):
    r = _get_redis()
    if not r:
        return
    try:
        pending = r.get(_REDIS_KEY)
        if pending:
            r.delete(_REDIS_KEY)
            await bot.send_message(
                chat_id=chat_id,
                text=f"ICARUS back online after auto-fix.\nFixed: {pending}",
            )
    except Exception as e:
        logging.warning(f"[AUTO-DEBUG] Startup check failed: {e}")
