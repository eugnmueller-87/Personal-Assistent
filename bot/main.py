import os
import tempfile
import logging
from datetime import time as dtime
from zoneinfo import ZoneInfo
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from openai import OpenAI
from google_client import get_this_week_events, get_unread_emails, get_today_events, get_recent_emails_with_ids
from github_client import get_open_issues, get_roadmap, create_issue
from claude_router import route, route_image, compose_morning_brief, is_email_urgent
from skills.email import get_pending_reply, clear_pending_reply, confirm_send_reply, set_edit_mode, is_edit_mode, update_pending_draft

BERLIN = ZoneInfo("Europe/Berlin")
_alerted_email_ids: set = set()

logging.basicConfig(level=logging.INFO)


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
        await update.message.reply_text(f"Error: {e}")


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
        await update.message.reply_text(f"Error: {e}")
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

    await update.message.reply_text("On it...")
    try:
        result = route(text, user_id=user_id)
        await _reply_with_approval(update, user_id, result)
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")


async def _reply_with_approval(update: Update, user_id: str, text: str):
    pending = get_pending_reply(user_id)
    if pending:
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("Send ✅", callback_data="reply_send"),
            InlineKeyboardButton("✏️ Edit", callback_data="reply_edit"),
            InlineKeyboardButton("Cancel ❌", callback_data="reply_cancel"),
        ]])
        await update.message.reply_text(text, reply_markup=keyboard)
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
        await query.message.reply_text(f"✅ {result}")
    elif query.data == "reply_edit":
        set_edit_mode(user_id)
        await query.message.reply_text("Send me the updated draft:")
    elif query.data == "reply_cancel":
        clear_pending_reply(user_id)
        await query.message.reply_text("Reply cancelled.")


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
    except Exception as e:
        logging.error(f"[ICARUS] morning_briefing failed: {e}")


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


def main():
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("calendar", calendar))
    app.add_handler(CommandHandler("emails", emails))
    app.add_handler(CommandHandler("issues", issues))
    app.add_handler(CommandHandler("summary", summary))
    app.add_handler(CommandHandler("roadmap", roadmap))
    app.add_handler(CommandHandler("task", task))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(handle_reply_callback))

    app.job_queue.run_daily(morning_briefing, time=dtime(hour=6, minute=0, tzinfo=BERLIN))
    app.job_queue.run_repeating(check_new_emails, interval=900, first=60)

    app.run_polling()


if __name__ == "__main__":
    main()
