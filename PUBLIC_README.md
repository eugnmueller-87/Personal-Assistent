# ICARUS — Personal AI Assistant

A self-hosted personal assistant that lives in Telegram. Powered by Claude AI. Reads and replies to emails, manages your calendar, searches the web, finds places, handles tasks — all from a single chat.

---

## What It Does

### Live Capabilities

| Capability | Detail |
|---|---|
| Natural language — text | Claude tool-use agent |
| Natural language — voice | Whisper transcription |
| Image / document analysis | Claude multimodal — invoices, contracts, whiteboards |
| Google Calendar | Read this week's events, create new events |
| Gmail | Read, search, full body, reply with approval flow |
| Proactive email alerts | Urgency-filtered, no spam |
| Morning briefing | Daily brief — calendar + emails + tasks |
| Web search | Live news, prices, company info, current events |
| Google Maps | Places, directions, opening hours, ratings |
| GitHub Issues | Read open tasks, create new ones |
| Multi-model routing | Fast model for simple queries, full model for complex |
| Persistent memory | Conversation history survives restarts |
| Health monitoring | Automated uptime check with instant alerts |
| Self-healing | Exceptions trigger a fix proposal for human review before deploy |

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
- _"Find a sushi place near Marienplatz"_ → Places + Maps link
- _"Add task: prepare Q2 review"_ → creates GitHub issue

---

## Tech Stack

| Component | Tool |
|---|---|
| Bot framework | python-telegram-bot |
| AI | Claude (Anthropic) |
| Voice | Whisper |
| Calendar | Google Calendar API |
| Email | Gmail API |
| Web search | Tavily |
| Maps | Google Maps APIs |
| Tasks | GitHub Issues API |
| Memory | Redis |
| Hosting | Railway |

---

## License

MIT — use it, fork it, make it yours.
