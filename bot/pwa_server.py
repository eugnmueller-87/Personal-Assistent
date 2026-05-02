import os
import uuid
import tempfile
import logging
from pathlib import Path
from fastapi import FastAPI, Request, Response, UploadFile, File, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from redis_ns import NS
from claude_router import route, route_image

logging.basicConfig(level=logging.INFO)

app = FastAPI()

PWA_PIN = os.environ.get("PWA_PIN", "1234")
USER_ID = "pwa"
_sessions: set = set()

MAX_ATTEMPTS = 5
LOCKOUT_SECONDS = 900  # 15 minutes
_fail_counts: dict = {}  # fallback if Redis unavailable


def _fail_key(ip: str) -> str:
    return f"{NS}:pwa:fail:{ip}"


def _check_lockout(ip: str):
    r = _get_redis()
    key = _fail_key(ip)
    count = int(r.get(key) or 0) if r else _fail_counts.get(ip, 0)
    if count >= MAX_ATTEMPTS:
        raise HTTPException(status_code=429, detail="Too many attempts. Try again in 15 minutes.")


def _record_failure(ip: str):
    r = _get_redis()
    key = _fail_key(ip)
    if r:
        r.incr(key)
        r.expire(key, LOCKOUT_SECONDS)
    else:
        _fail_counts[ip] = _fail_counts.get(ip, 0) + 1


def _clear_failures(ip: str):
    r = _get_redis()
    if r:
        r.delete(_fail_key(ip))
    else:
        _fail_counts.pop(ip, None)


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


def _valid_session(token: str) -> bool:
    if not token:
        return False
    r = _get_redis()
    if r:
        return bool(r.get(f"{NS}:pwa:session:{token}"))
    return token in _sessions


def _create_session() -> str:
    token = str(uuid.uuid4())
    r = _get_redis()
    if r:
        r.set(f"{NS}:pwa:session:{token}", "1", ex=604800)  # 7 days
    else:
        _sessions.add(token)
    return token


def _delete_session(token: str):
    r = _get_redis()
    if r:
        r.delete(f"{NS}:pwa:session:{token}")
    _sessions.discard(token)


def _auth(request: Request):
    token = request.cookies.get("pwa_session")
    if not _valid_session(token):
        raise HTTPException(status_code=401, detail="Unauthorized")
    return token


@app.post("/api/login")
async def login(request: Request, response: Response):
    ip = request.client.host
    _check_lockout(ip)
    body = await request.json()
    if body.get("pin") != PWA_PIN:
        _record_failure(ip)
        logging.warning(f"[PWA] failed login from {ip}")
        raise HTTPException(status_code=401, detail="Wrong PIN")
    _clear_failures(ip)
    token = _create_session()
    response.set_cookie(
        "pwa_session", token,
        httponly=True, samesite="strict", max_age=604800
    )
    return {"ok": True}


@app.post("/api/logout")
async def logout(request: Request, response: Response):
    token = request.cookies.get("pwa_session")
    if token:
        _delete_session(token)
    response.delete_cookie("pwa_session")
    return {"ok": True}


@app.post("/api/chat")
async def chat(request: Request):
    _auth(request)
    body = await request.json()
    text = body.get("message", "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Empty message")
    logging.info(f"[PWA] chat: {text[:60]!r}")
    result = route(text, user_id=USER_ID)
    return {"reply": result}


@app.post("/api/voice")
async def voice(request: Request, file: UploadFile = File(...)):
    _auth(request)
    content_type = file.content_type or "audio/webm"
    suffix = ".webm" if "webm" in content_type else ".ogg"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name
    try:
        from openai import OpenAI
        whisper = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
        with open(tmp_path, "rb") as audio:
            transcript = whisper.audio.transcriptions.create(
                model="whisper-1", file=audio
            )
        text = transcript.text
        logging.info(f"[PWA] voice: {text[:60]!r}")
        result = route(text, user_id=USER_ID)
        return {"transcript": text, "reply": result}
    finally:
        os.unlink(tmp_path)


@app.post("/api/photo")
async def photo(
    request: Request,
    file: UploadFile = File(...),
    caption: str = Form(""),
):
    _auth(request)
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name
    try:
        with open(tmp_path, "rb") as f:
            image_bytes = f.read()
        logging.info(f"[PWA] photo: {len(image_bytes)//1024}KB caption={caption!r}")
        result = route_image(image_bytes, caption=caption, user_id=USER_ID)
        return {"reply": result}
    finally:
        os.unlink(tmp_path)


@app.get("/health")
async def health():
    return {"status": "ok"}


static_dir = Path(__file__).parent / "static"
app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")
