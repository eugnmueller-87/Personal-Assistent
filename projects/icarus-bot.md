# ICARUS Telegram — Command Center

**Bot:** @IcarusORG_bot
**Status:** Live — fully operational
**Hosting:** Railway (free tier, always-on)
**Public repo:** github.com/eugnmueller-87/Personal-Assistent
**Role:** The single interface for all agents, projects, and personal ops. You talk to ICARUS. ICARUS commands everything else.

---

## Vision

```
ICARUS Telegram (the only interface you need)
     │
     ├── Personal ops        — calendar, email, tasks, memory (live)
     ├── Spend Lens agents   — trigger analyses, surface insights (planned)
     ├── Marketing agent     — draft + post LinkedIn updates (planned)
     └── Future agents       — plug in as tools, report back here
```

---

## Live Capabilities

| Capability | Detail |
|---|---|
| Commands | /calendar, /emails, /issues, /summary, /roadmap, /task |
| Natural language — text | Claude Sonnet 4.6 tool-use agent |
| Natural language — voice | OpenAI Whisper transcription |
| Image / document analysis | Claude multimodal — invoices, contracts, whiteboards |
| Google Calendar read | This week's events |
| Google Calendar write | Create events from voice or text |
| Gmail read | Important-only, last 3 days default, time-based queries |
| Gmail full body | get_email_body — fetches format=full, extracts plain text |
| Gmail search | search_emails — returns body directly when single result found |
| Email reply | Send / Edit / Cancel approval flow from Telegram |
| Proactive email alerts | Polls every 15 min, Haiku judges urgency, no spam |
| Morning briefing | 06:00 Berlin, Claude-composed daily brief |
| GitHub Issues | Read open tasks, create new ones |
| Roadmap reader | Reads any project markdown from private repo |
| Web search | Tavily API — live news, prices, company info, current events |
| Google Maps | Places API + Directions API — find places, hours, ratings, travel time |
| Multi-model routing | Haiku for simple, Sonnet 4.6 for complex (~€4/month) |
| Persistent memory | Upstash Redis — survives restarts and redeploys |

---

## Planned

### Personal ops (remaining)
- [ ] Weekly AI summary — Claude reviews the week, suggests priorities

### Agent hub (next phase)
- [ ] Spend Lens connection — trigger analyses, receive procurement alerts
- [ ] LinkedIn marketing agent — Claude drafts, ICARUS previews, you confirm
- [ ] Agent status overview — "what are all my agents doing?" in one message

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
| Tasks | GitHub Issues API |
| Memory | Upstash Redis (free tier) |
| Hosting | Railway (free tier) |
| Scheduling | APScheduler via job_queue |

## Environment Variables

| Variable | Source |
|---|---|
| TELEGRAM_BOT_TOKEN | BotFather |
| TELEGRAM_CHAT_ID | Your Telegram user ID |
| ANTHROPIC_API_KEY | console.anthropic.com |
| OPENAI_API_KEY | platform.openai.com |
| GITHUB_TOKEN | github.com/settings/tokens (no expiry) |
| GITHUB_REPO | username/repo-name |
| GOOGLE_CLIENT_ID | Google Cloud Console |
| GOOGLE_CLIENT_SECRET | Google Cloud Console |
| GOOGLE_REFRESH_TOKEN | gcal_auth.py output |
| UPSTASH_REDIS_URL | upstash.com |
| UPSTASH_REDIS_TOKEN | upstash.com |
