import os
import asyncio
import tempfile
import logging
import threading
from datetime import time as dtime
from zoneinfo import ZoneInfo
from http.server import HTTPServer, BaseHTTPRequestHandler
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


class _HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"ok")
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, *args):
        pass


def _start_health_server():
    port = int(os.environ.get("PORT", 8080))
    HTTPServer(("0.0.0.0", port), _HealthHandler).serve_forever()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "ICARUS online.\n\n"
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
    allowed_id = os.environ.get("TELEGRAM_CHAT_ID", "")
    if user_id != allowed_id:
        return

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
    allowed_id = os.environ.get("TELEGRAM_CHAT_ID", "")
    if user_id != allowed_id:
        return

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
    allowed_id = os.environ.get("TELEGRAM_CHAT_ID", "")
    if user_id != allowed_id:
        return

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


async def morning_briefing(context):
    try:
        cal = get_today_events()
        mail = get_unread_emails(since_minutes=1440)
        iss = get_open_issues()
        brief = compose_morning_brief(cal, mail, iss)
        await context.bot.send_message(
            chat_id=os.environ["TELEGRAM_CHAT_ID"],
            text=f"☀️ Morning brief\n\n{brief}",
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
        import traceback as _tb
        logging.error(f"[ICARUS] check_new_emails failed: {e}")
        asyncio.create_task(handle_error(e, _tb.format_exc()))


async def audit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    events = get_recent_events(20)
    if not events:
        await update.message.reply_text("No audit events recorded yet.")
        return
    lines = [f"[{e['ts']}] {e['type']}: {e['detail']}" for e in events]
    await update.message.reply_text("Audit log (last 20):\n\n" + "\n".join(lines))


def main():
    threading.Thread(target=_start_health_server, daemon=True).start()

    token = os.environ["TELEGRAM_BOT_TOKEN"]
    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("calendar", calendar))
    app.add_handler(CommandHandler("emails", emails))
    app.add_handler(CommandHandler("issues", issues))
    app.add_handler(CommandHandler("summary", summary))
    app.add_handler(CommandHandler("roadmap", roadmap))
    app.add_handler(CommandHandler("task", task))
    app.add_handler(CommandHandler("audit", audit))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(handle_reply_callback))

    app.job_queue.run_daily(morning_briefing, time=dtime(hour=6, minute=0, tzinfo=BERLIN))
    app.job_queue.run_repeating(check_new_emails, interval=900, first=60)

    app.run_polling()


if __name__ == "__main__":
    main()
