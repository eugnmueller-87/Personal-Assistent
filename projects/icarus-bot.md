# ICARUS — Interactive Telegram Bot

**Bot:** @IcarusORG_bot  
**Status:** Planning — bot live, interactive layer not yet built  
**Hosting:** Railway (free tier)  

---

## Goal

A personal AI assistant accessible from Telegram. Send a message, get a real response. No server to manage, works from phone anywhere.

---

## Roadmap

### Phase A — Foundation (Next)
- [ ] Set up Railway account + connect to GitHub repo
- [ ] Create `bot/main.py` with `python-telegram-bot`
- [ ] Store Google refresh token + client credentials as Railway env vars
- [ ] Deploy to Railway — bot stays online 24/7

### Phase B — Core Commands
- [ ] `/calendar` — this week's Google Calendar events
- [ ] `/emails` — unread Gmail summary (count, senders, subjects)
- [ ] `/issues` — open GitHub issues from ORG-EUGEN
- [ ] `/summary` — everything combined in one message
- [ ] `/roadmap [project]` — status of any active roadmap

### Phase C — Natural Language
- [ ] Free text handled by Claude API
- [ ] "Any emails from suppliers today?" → Gmail query
- [ ] "What's next on SpendLens?" → reads projects/spend-lens.md
- [ ] "Add task: call Stefan" → creates GitHub issue

### Phase D — Proactive Alerts
- [ ] Monday: weekly review + calendar + email digest (replaces GitHub Action notification)
- [ ] Daily: morning briefing (optional, on request)
- [ ] Triggered: alert when new GitHub issue created

---

## Technical Stack

| Component | Tool |
|-----------|------|
| Bot framework | python-telegram-bot |
| NLP / routing | Claude API (Haiku for speed) |
| Calendar | Google Calendar API (token stored in Railway env) |
| Email | Gmail API (same token) |
| GitHub | GitHub API (GITHUB_TOKEN) |
| Hosting | Railway (free tier, always-on) |

---

## Credentials Needed in Railway

| Variable | Source |
|----------|--------|
| `TELEGRAM_BOT_TOKEN` | BotFather |
| `TELEGRAM_CHAT_ID` | Already known |
| `ANTHROPIC_API_KEY` | .env |
| `GITHUB_TOKEN` | .env |
| `GOOGLE_CLIENT_ID` | credentials/google_calendar.json |
| `GOOGLE_CLIENT_SECRET` | credentials/google_calendar.json |
| `GOOGLE_REFRESH_TOKEN` | credentials/token.json → refresh_token field |

---

## Files to Create

```
bot/
├── main.py           — entry point, bot setup, command routing
├── calendar_client.py — Google Calendar functions
├── gmail_client.py   — Gmail functions
├── github_client.py  — GitHub API functions
└── claude_router.py  — Claude routes free-text to right function
requirements.txt      — python-telegram-bot, google libs, anthropic
```
