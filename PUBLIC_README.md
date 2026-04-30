# ICARUS — Personal AI Assistant

A self-hosted personal assistant that lives in Telegram. Powered by Claude AI. Reads and replies to emails, manages your calendar, searches the web, finds places, handles tasks — all from a single chat. Deployed on Railway, always on.

---

## What It Does

### Live Capabilities

| Capability | Detail |
|---|---|
| Natural language — text | Claude Sonnet 4.6 tool-use agent |
| Natural language — voice | OpenAI Whisper transcription |
| Image / document analysis | Claude multimodal — invoices, contracts, whiteboards |
| Google Calendar read | This week's events |
| Google Calendar write | Create events from voice or text |
| Gmail read | Important-only, last 3 days, time-based queries |
| Gmail search | Find any email by person, subject, folder, or date |
| Gmail full body | Read the actual message content |
| Email reply | Draft + Send / Edit / Cancel approval flow |
| Proactive email alerts | Polls every 15 min, AI urgency filter, no spam |
| Morning briefing | 06:00 Berlin — calendar + emails + tasks |
| Web search | Tavily API — live news, prices, company info |
| Google Maps | Places, directions, opening hours, ratings |
| GitHub Issues | Read open tasks, create new ones |
| Roadmap reader | Read any project markdown from repo |
| Multi-model routing | Haiku for simple, Sonnet for complex (~€4/month) |
| Persistent memory | Upstash Redis — survives restarts |

### Commands
| Command | What it does |
|---------|-------------|
| `/calendar` | This week's events |
| `/emails` | Unread important emails |
| `/issues` | Open GitHub tasks |
| `/summary` | Calendar + emails + tasks combined |
| `/roadmap [project]` | Any project roadmap |
| `/task [text]` | Create a GitHub issue |

### Natural Language Examples
- _"Show me the email from Eve"_ → reads full body
- _"Reply to Stefan: confirmed for Thursday"_ → stages reply for approval
- _"What's the weather in Munich tomorrow?"_ → live web search
- _"Find a sushi place near Marienplatz"_ → Places API + Maps link
- _"How long from Munich to Berlin by train?"_ → Directions API
- _"Add task: prepare Q2 review"_ → creates GitHub issue

---

## Tech Stack

| Component | Tool |
|---|---|
| Bot framework | python-telegram-bot[job-queue] |
| AI — complex | Claude Sonnet 4.6 (tool-use agent) |
| AI — simple | Claude Haiku 4.5 (fast routing) |
| AI — images | Claude Sonnet 4.6 (multimodal) |
| Voice | OpenAI Whisper API |
| Calendar | Google Calendar API (read + write) |
| Email | Gmail API (modify scope) |
| Web search | Tavily API |
| Maps | Google Places API + Directions API |
| Tasks | GitHub Issues API |
| Memory | Upstash Redis (free tier) |
| Hosting | Railway (free tier) |
| Scheduling | APScheduler via job_queue |

---

## Environment Variables

```env
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
ANTHROPIC_API_KEY=
OPENAI_API_KEY=
GITHUB_TOKEN=
GITHUB_REPO=
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REFRESH_TOKEN=
UPSTASH_REDIS_URL=
UPSTASH_REDIS_TOKEN=
TAVILY_API_KEY=
GOOGLE_MAPS_API_KEY=
```

---

## Architecture

```
Telegram (you)
     │
     ▼
python-telegram-bot (Railway, always-on)
     │
     ├── voice  → Whisper → text → claude_router
     ├── photo  → Claude Sonnet (multimodal)
     └── text   → _pick_model() → Haiku or Sonnet
                       └── tool-use agent loop
                             ├── get_calendar / create_calendar_event
                             ├── get_emails / search_emails / get_email_body
                             ├── stage_email_reply → send_reply
                             ├── get_issues / create_issue / get_roadmap
                             ├── web_search (Tavily)
                             └── find_place / get_directions (Google Maps)
```

---

## License

MIT — use it, fork it, make it yours.
