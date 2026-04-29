# Personal Assistant — AI-powered Telegram Bot

A self-hosted personal assistant that lives in Telegram. Ask it about your calendar, emails, and tasks. Get proactive briefings every morning. Powered by Claude AI, Google APIs, and GitHub — deployed on Railway for free.

---

## What It Does

### Live — Notifications
- **Monday briefing** — weekly review issue created automatically, pushed to Telegram with this week's calendar and email digest
- **Daily morning brief** — unread emails, today's calendar, open tasks (optional)

### Live — Integrations
- **Google Calendar** — read and query your events
- **Gmail** — read, summarize, and manage emails (modify scope)
- **GitHub** — read issues, todos, and roadmaps from your repo

### Interactive Commands (via Telegram)
| Command | What it does |
|---------|-------------|
| `/calendar` | Show this week's events |
| `/emails` | Unread email summary — count, senders, subjects |
| `/issues` | Open GitHub issues |
| `/summary` | Everything combined in one message |
| `/roadmap [project]` | Status of any active project roadmap |

### Natural Language (Claude-powered)
Ask anything in plain text:
- _"Any emails from suppliers today?"_
- _"What's on my calendar Thursday?"_
- _"What's next on the roadmap?"_
- _"Add task: call Stefan"_ → creates a GitHub issue

---

## Planned Features

- [ ] Voice message support — transcribe and process
- [ ] Proactive alerts — notify when flagged emails arrive
- [ ] Task creation from Telegram → syncs to GitHub Issues
- [ ] Weekly AI summary — Claude summarizes the week and suggests priorities
- [ ] Whiteboard integration (Excalidraw / Miro)
- [ ] Multi-project roadmap tracking
- [ ] n8n / Make.com workflow triggers

---

## Tech Stack

| Layer | Tool |
|-------|------|
| Bot framework | python-telegram-bot |
| AI / NLP | Claude API (Anthropic) — Haiku for speed |
| Calendar | Google Calendar API |
| Email | Gmail API |
| Task tracking | GitHub Issues + API |
| Hosting | Railway (free tier, always-on) |
| Auth | Google OAuth 2.0 (Desktop app flow) |
| Scheduling | GitHub Actions (cron) |

---

## Architecture

```
Telegram (you)
     │
     ▼
python-telegram-bot (Railway)
     │
     ├── /calendar → Google Calendar API
     ├── /emails   → Gmail API
     ├── /issues   → GitHub API
     ├── /summary  → all three combined
     └── free text → Claude API → routes to right function

GitHub Actions (cron)
     └── Monday 08:00 UTC
           ├── Create weekly review issue
           ├── Fetch calendar events
           ├── Fetch email digest
           └── Push to Telegram
```

---

## Setup

### 1. Clone and configure
```bash
git clone https://github.com/your-username/personal-assistant
cd personal-assistant
```

### 2. Create a Telegram bot
- Message `@BotFather` → `/newbot`
- Save the bot token

### 3. Google API credentials
- Go to [Google Cloud Console](https://console.cloud.google.com)
- Create a project → enable **Google Calendar API** and **Gmail API**
- Create **OAuth client ID** → type: **Desktop app**
- Download `credentials.json`
- Run `python workflows/gcal_auth.py` to authenticate
- Scopes required:
  - `https://www.googleapis.com/auth/calendar`
  - `https://www.googleapis.com/auth/gmail.modify`

### 4. Environment variables
```env
TELEGRAM_BOT_TOKEN=your_token
TELEGRAM_CHAT_ID=your_chat_id
ANTHROPIC_API_KEY=your_key
GITHUB_TOKEN=your_token
GITHUB_REPO=your-username/your-repo
GOOGLE_CLIENT_ID=from_credentials.json
GOOGLE_CLIENT_SECRET=from_credentials.json
GOOGLE_REFRESH_TOKEN=from_token.json
```

### 5. Deploy to Railway
- Connect your GitHub repo to [Railway](https://railway.app)
- Add all environment variables
- Deploy — bot stays online 24/7

---

## Project Status

| Feature | Status |
|---------|--------|
| Telegram bot | Live |
| Google Calendar API | Live |
| Gmail API | Live |
| Monday GitHub Action | Live |
| Interactive bot (Railway) | In progress |
| Natural language routing | Planned |
| Voice messages | Planned |

---

## License

MIT — use it, fork it, make it yours.
