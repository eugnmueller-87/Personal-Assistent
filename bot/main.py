import os
import asyncio
import tempfile
import logging
import uvicorn
from contextlib import asynccontextmanager
from datetime import time as dtime
from zoneinfo import ZoneInfo
from fastapi import FastAPI, Request, Response
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from openai import OpenAI
from google_client import get_this_week_events, get_unread_emails, get_today_events, get_recent_emails_with_ids
from github_client import get_open_issues, get_roadmap, create_issue
from claude_router import route, route_image, compose_morning_brief, is_email_urgent
from skills.email import get_pending_reply, clear_pending_reply, confirm_send_reply, set_edit_mode, is_edit_mode, update_pending_draft
from linkedin_client import get_pending_post, clear_pending_post, confirm_post, update_pending_post
from auto_debug import handle_error
from audit_log import log_event, get_recent_events

BERLIN = ZoneInfo("Europe/Berlin")
_alerted_email_ids: set = set()

logging.basicConfig(level=logging.INFO)



def _allowed_filter():
    allowed = os.environ.get("TELEGRAM_CHAT_ID")
    if not allowed:
        raise RuntimeError("TELEGRAM_CHAT_ID must be set — refusing to start without owner auth")
    return filters.User(user_id=int(allowed))


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "ICARUS online. [v76dcc0a]\n\n"
        "Commands:\n"
        "/calendar — this week's events\n"
        "/emails — unread emails\n"
        "/issues — open GitHub issues\n"
        "/summary — everything\n"
        "/roadmap [project] — roadmap status\n"
        "/task [title] — create a GitHub issue\n\n"
        "Or just ask me anything — text, voice, or photo."
    )


async def calendar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Fetching calendar...")
    try:
        result = get_this_week_events()
    except Exception as e:
        result = f"Calendar unavailable: {e}"
    await update.message.reply_text(f"📅 This week:\n\n{result}")


async def emails(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Checking inbox...")
    try:
        result = get_unread_emails()
    except Exception as e:
        result = f"Email unavailable: {e}"
    await update.message.reply_text(f"📧 Emails:\n\n{result}")


async def issues(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Fetching issues...")
    try:
        result = get_open_issues()
    except Exception as e:
        result = f"GitHub unavailable: {e}"
    await update.message.reply_text(f"📋 GitHub:\n\n{result}")


async def summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Pulling everything together...")
    try:
        cal = get_this_week_events()
    except Exception as e:
        cal = f"Calendar unavailable: {e}"
    try:
        mail = get_unread_emails()
    except Exception as e:
        mail = f"Email unavailable: {e}"
    try:
        iss = get_open_issues()
    except Exception as e:
        iss = f"GitHub unavailable: {e}"
    await update.message.reply_text(
        f"📅 Calendar:\n{cal}\n\n"
        f"📧 Emails:\n{mail}\n\n"
        f"📋 Issues:\n{iss}"
    )


async def roadmap(update: Update, context: ContextTypes.DEFAULT_TYPE):
    project = " ".join(context.args) if context.args else "org-eugen"
    await update.message.reply_text(f"Loading {project} roadmap...")
    try:
        result = get_roadmap(project)
    except Exception as e:
        result = f"Roadmap unavailable: {e}"
    await update.message.reply_text(result)


async def task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /task Buy train tickets")
        return
    title = " ".join(context.args)
    try:
        result = create_issue(title)
    except Exception as e:
        result = f"Failed to create task: {e}"
    await update.message.reply_text(f"✅ {result}")


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    await update.message.reply_text("Transcribing...")

    voice_file = await context.bot.get_file(update.message.voice.file_id)

    with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
        await voice_file.download_to_drive(tmp.name)
        tmp_path = tmp.name

    text = None
    try:
        whisper = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
        with open(tmp_path, "rb") as audio:
            transcript = whisper.audio.transcriptions.create(
                model="whisper-1",
                file=audio,
            )
        text = transcript.text
    except Exception as e:
        await update.message.reply_text(f"Transcription failed: {e}")
    finally:
        os.unlink(tmp_path)

    if not text:
        return

    await update.message.reply_text(f'"{text}"')
    try:
        result = route(text, user_id=user_id)
        await _reply_with_approval(update, user_id, result)
    except Exception as e:
        import traceback as _tb
        asyncio.create_task(handle_error(e, _tb.format_exc()))
        await update.message.reply_text("Hit an error. Auto-fixing — back in ~2 min.")


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    await update.message.reply_text("Reading image...")

    photo_file = await context.bot.get_file(update.message.photo[-1].file_id)

    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        await photo_file.download_to_drive(tmp.name)
        tmp_path = tmp.name

    try:
        with open(tmp_path, "rb") as f:
            image_bytes = f.read()
        caption = update.message.caption or ""
        result = route_image(image_bytes, caption=caption, user_id=user_id)
        await update.message.reply_text(result)
    except Exception as e:
        import traceback as _tb
        asyncio.create_task(handle_error(e, _tb.format_exc()))
        await update.message.reply_text("Hit an error. Auto-fixing — back in ~2 min.")
    finally:
        os.unlink(tmp_path)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    text = update.message.text

    if is_edit_mode(user_id):
        pending = get_pending_reply(user_id)
        if pending:
            update_pending_draft(user_id, text)
            preview = (
                f"Draft updated:\n\n{text}\n\n"
                f"To: {pending['to']}"
            )
            await _reply_with_approval(update, user_id, preview)
        else:
            update_pending_draft(user_id, text)
            await update.message.reply_text("No pending reply found.")
        return

    if get_pending_post(user_id):
        update_pending_post(user_id, text)
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("Post ✅", callback_data="linkedin_post"),
            InlineKeyboardButton("✏️ Edit", callback_data="linkedin_edit"),
            InlineKeyboardButton("Cancel ❌", callback_data="linkedin_cancel"),
        ]])
        await update.message.reply_text(f"Updated draft:\n\n{text}", reply_markup=keyboard)
        return

    await update.message.reply_text("On it...")
    try:
        result = route(text, user_id=user_id)
        await _reply_with_approval(update, user_id, result)
    except Exception as e:
        import traceback as _tb
        asyncio.create_task(handle_error(e, _tb.format_exc()))
        await update.message.reply_text("Hit an error. Auto-fixing — back in ~2 min.")


async def _reply_with_approval(update: Update, user_id: str, text: str):
    pending_email = get_pending_reply(user_id)
    pending_linkedin = get_pending_post(user_id)

    if pending_email:
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("Send ✅", callback_data="reply_send"),
            InlineKeyboardButton("✏️ Edit", callback_data="reply_edit"),
            InlineKeyboardButton("Cancel ❌", callback_data="reply_cancel"),
        ]])
        await update.message.reply_text(text, reply_markup=keyboard)
    elif pending_linkedin or (isinstance(text, str) and text.startswith("LINKEDIN_STAGED:")):
        post_text = text.replace("LINKEDIN_STAGED:", "").strip() if text.startswith("LINKEDIN_STAGED:") else text
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("Post ✅", callback_data="linkedin_post"),
            InlineKeyboardButton("✏️ Edit", callback_data="linkedin_edit"),
            InlineKeyboardButton("Cancel ❌", callback_data="linkedin_cancel"),
        ]])
        await update.message.reply_text(f"Draft:\n\n{post_text}", reply_markup=keyboard)
    else:
        await update.message.reply_text(text)


async def handle_reply_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = str(query.from_user.id)
    allowed_id = os.environ.get("TELEGRAM_CHAT_ID", "")
    if user_id != allowed_id:
        await query.answer()
        return

    await query.answer()
    await query.edit_message_reply_markup(reply_markup=None)

    if query.data == "reply_send":
        result = confirm_send_reply(user_id)
        log_event("email_reply_sent", result[:100])
        await query.message.reply_text(f"✅ {result}")
    elif query.data == "reply_edit":
        set_edit_mode(user_id)
        await query.message.reply_text("Send me the updated draft:")
    elif query.data == "reply_cancel":
        clear_pending_reply(user_id)
        await query.message.reply_text("Reply cancelled.")
    elif query.data == "linkedin_post":
        result = confirm_post(user_id)
        log_event("linkedin_posted", result[:100])
        await query.message.reply_text(f"✅ {result}")
    elif query.data == "linkedin_edit":
        await query.message.reply_text("Send me the updated post text:")
    elif query.data == "linkedin_cancel":
        clear_pending_post(user_id)
        await query.message.reply_text("Post cancelled.")


def _hermes_morning_signals() -> str:
    """Fetch top 3 HIGH-urgency Hermes signals for the morning brief. Never raises."""
    try:
        from skills.hermes import _hermes_briefing
        return _hermes_briefing(limit=3)
    except Exception as e:
        logging.warning(f"[ICARUS] hermes morning signals failed: {e}")
        return ""


async def hermes_weekly_digest(context):
    """Send the weekly Hermes digest every Sunday at 18:30 Berlin."""
    try:
        from skills.hermes import _hermes_digest
        digest_text = _hermes_digest()
        if digest_text and "No weekly digest" not in digest_text:
            await context.bot.send_message(
                chat_id=os.environ["TELEGRAM_CHAT_ID"],
                text=f"📊 Weekly Hermes digest\n\n{digest_text}",
            )
            log_event("hermes_weekly_digest", "sent ok")
    except Exception as e:
        logging.error(f"[ICARUS] hermes_weekly_digest failed: {e}")


async def morning_briefing(context):
    try:
        cal = get_today_events()
        mail = get_unread_emails(since_minutes=1440)
        iss = get_open_issues()
        brief = compose_morning_brief(cal, mail, iss)
        hermes_block = _hermes_morning_signals()
        market_section = f"\n\n📡 Market signals:\n{hermes_block}" if hermes_block else ""
        await context.bot.send_message(
            chat_id=os.environ["TELEGRAM_CHAT_ID"],
            text=f"☀️ Morning brief\n\n{brief}{market_section}",
        )
        log_event("morning_briefing", "sent ok")
    except Exception as e:
        import traceback as _tb
        logging.error(f"[ICARUS] morning_briefing failed: {e}")
        log_event("morning_briefing_failed", str(e)[:100])
        asyncio.create_task(handle_error(e, _tb.format_exc()))


async def check_new_emails(context):
    global _alerted_email_ids
    try:
        formatted, msg_ids = get_recent_emails_with_ids(since_minutes=20)
        if not msg_ids:
            return
        new_ids = msg_ids - _alerted_email_ids
        if not new_ids:
            return
        _alerted_email_ids.update(new_ids)
        if is_email_urgent(formatted):
            await context.bot.send_message(
                chat_id=os.environ["TELEGRAM_CHAT_ID"],
                text=f"📧 Heads up:\n\n{formatted}",
            )
    except Exception as e:
        logging.error(f"[ICARUS] check_new_emails failed: {e}")


async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("pong")


async def audit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    events = get_recent_events(20)
    if not events:
        await update.message.reply_text("No audit events recorded yet.")
        return
    lines = [f"[{e['ts']}] {e['type']}: {e['detail']}" for e in events]
    await update.message.reply_text("Audit log (last 20):\n\n" + "\n".join(lines))


async def tools(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lines = []
    try:
        from skills import get_all_tools
        t = get_all_tools()
        lines.append(f"{len(t)} tools: {', '.join(x['name'] for x in t)}")
    except Exception as e:
        lines.append(f"get_all_tools error: {e}")
    try:
        from skills import hermes
        lines.append(f"hermes.TOOLS count: {len(hermes.TOOLS)}")
    except Exception as e:
        lines.append(f"hermes import error: {e}")
    await update.message.reply_text("\n".join(lines))


async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from claude_router import clear_history
    user_id = str(update.effective_user.id)
    clear_history(user_id)
    await update.message.reply_text("History cleared. Fresh start.")


async def chart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    import requests as _req
    chart_type = context.args[0] if context.args else "signals"
    if chart_type not in ("signals", "landscape"):
        await update.message.reply_text("Usage: /chart signals  or  /chart landscape")
        return
    hermes_url = os.environ.get("HERMES_URL", "").rstrip("/")
    hermes_key = os.environ.get("HERMES_API_KEY", "")
    if not hermes_url:
        await update.message.reply_text("HERMES_URL not set in environment.")
        return
    await update.message.reply_text(f"Building {chart_type} chart...")
    try:
        headers = {"x-api-key": hermes_key} if hermes_key else {}
        r = _req.get(f"{hermes_url}/chart/{chart_type}", headers=headers, timeout=30)
        r.raise_for_status()
        chart_url = r.json()["url"]
        await context.bot.send_photo(chat_id=update.effective_chat.id, photo=chart_url)
    except Exception as e:
        await update.message.reply_text(f"Chart failed: {e}")


def main():
    from skills import get_all_tools
    _loaded_tools = get_all_tools()
    print(f"[ICARUS] Loaded {len(_loaded_tools)} tools: {[t['name'] for t in _loaded_tools]}", flush=True)

    token = os.environ["TELEGRAM_BOT_TOKEN"]
    webhook_url = os.environ["WEBHOOK_URL"].rstrip("/")

    app = Application.builder().token(token).build()

    auth = _allowed_filter()

    app.add_handler(CommandHandler("ping", ping))
    app.add_handler(CommandHandler("start", start, filters=auth))
    app.add_handler(CommandHandler("calendar", calendar, filters=auth))
    app.add_handler(CommandHandler("emails", emails, filters=auth))
    app.add_handler(CommandHandler("issues", issues, filters=auth))
    app.add_handler(CommandHandler("summary", summary, filters=auth))
    app.add_handler(CommandHandler("roadmap", roadmap, filters=auth))
    app.add_handler(CommandHandler("task", task, filters=auth))
    app.add_handler(CommandHandler("audit", audit, filters=auth))
    app.add_handler(CommandHandler("tools", tools, filters=auth))
    app.add_handler(CommandHandler("clear", clear, filters=auth))
    app.add_handler(CommandHandler("chart", chart, filters=auth))
    app.add_handler(MessageHandler(filters.VOICE & auth, handle_voice))
    app.add_handler(MessageHandler(filters.PHOTO & auth, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & auth, handle_message))
    app.add_handler(CallbackQueryHandler(handle_reply_callback))

    app.job_queue.run_daily(morning_briefing, time=dtime(hour=6, minute=0, tzinfo=BERLIN))
    app.job_queue.run_daily(hermes_weekly_digest, time=dtime(hour=18, minute=30, tzinfo=BERLIN), days=(6,))
    app.job_queue.run_repeating(check_new_emails, interval=900, first=60)

    @asynccontextmanager
    async def lifespan(_fast):
        await app.initialize()
        await app.start()
        await app.bot.set_webhook(url=f"{webhook_url}/telegram", drop_pending_updates=True)
        logging.info(f"[ICARUS] Webhook registered at {webhook_url}/telegram")
        yield
        await app.bot.delete_webhook()
        await app.stop()
        await app.shutdown()

    fast_app = FastAPI(lifespan=lifespan)

    @fast_app.get("/health")
    async def health():
        return Response("ok", media_type="text/plain")

    @fast_app.post("/telegram")
    async def telegram_webhook(request: Request):
        data = await request.json()
        update = Update.de_json(data, app.bot)
        await app.update_queue.put(update)
        return Response("ok", media_type="text/plain")

    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(fast_app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
