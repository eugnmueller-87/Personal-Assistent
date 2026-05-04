# ICARUS Telegram — Command Center

**Status:** Live — fully operational
**Role:** The single interface for all agents, projects, and personal ops. You talk to ICARUS. ICARUS commands everything else.

---

## Vision

```
ICARUS Telegram (the only interface you need)
     │
     ├── Personal ops        — calendar, email, tasks, memory (live)
     ├── Spend Lens agents   — trigger analyses, surface insights (planned)
     ├── Marketing agent     — draft + post LinkedIn updates (live)
     └── Future agents       — plug in as tools, report back here
```

---

## Live Capabilities

| Capability | Detail |
|---|---|
| Commands | /calendar, /emails, /issues, /summary, /roadmap, /task, /audit |
| Natural language — text | Claude tool-use agent |
| Natural language — voice | Whisper transcription |
| Image / document analysis | Claude multimodal — invoices, contracts, whiteboards |
| Google Calendar read | This week's events |
| Google Calendar write | Create events from voice or text |
| Gmail read | Important-only, last 3 days default, time-based queries |
| Gmail full body | Fetches and extracts plain text |
| Gmail search | Returns body directly when single result found |
| Email reply | Send / Edit / Cancel approval flow from Telegram |
| Proactive email alerts | Polls every 15 min, AI judges urgency, no spam |
| Morning briefing | 06:00 Berlin, Claude-composed daily brief |
| GitHub Issues | Read open tasks, create new ones |
| Roadmap reader | Reads any project markdown from private repo |
| Web search | Live news, prices, company info, current events |
| Google Maps | Places + Directions — find places, hours, ratings, travel time |
| Shopping list | Add/remove/clear items conversationally — persisted in Redis |
| Expense tracker | Log by text or receipt photo — weekly/monthly summary by store |
| LinkedIn posts | Draft, preview, confirm/edit/cancel approval flow from Telegram |
| Audit log | /audit shows last 20 system events |
| Multi-model routing | Fast model for simple, full model for complex |
| Persistent memory | Survives restarts and redeploys |
| Sandbox environment | icarus-dev on Railway — separate bot token, Redis namespace isolated |
| PWA — icarusai.de | JARVIS HUD UI: text, voice, photo, PIN auth — HTTPS, installable on iPhone |

---

## Planned

### Now — low & medium effort (direct to prod)

**Task & Calendar upgrades**
- [ ] Update/close GitHub issues — edit title, body, state via conversation
- [ ] Update existing calendar events — modify time, title, location, attendees
- [ ] Calendar focus blocking — "block 2h tomorrow morning for deep work"

**Personal knowledge**
- [ ] Personal notes — store and retrieve notes conversationally via Redis
- [ ] Google Drive access — read/list files, open docs from conversation

**Reminders**
- [ ] One-off reminders — "remind me in 2h", persisted and fired via APScheduler
- [ ] Recurring alarms — "every Monday 9am" job stored in Redis, survives redeploy

### Later — heavy effort (parked)
- [ ] Fitness / sleep / health tracking — Apple Health, Garmin, or Oura integration
- [ ] Slack / Teams integration — send and receive messages from Telegram
- [ ] SMS / phone calls — Twilio or similar, separate cost model

### Personal ops (remaining)
- [ ] Weekly AI summary — Claude reviews the week, suggests priorities
- [ ] Voice output (TTS) — ICARUS talks back
- [ ] Smarter proactivity — "meeting in 10 min", "Stefan hasn't replied in 3 days"

### Agent hub (next phase)
- [x] Staging environment — dev branch + Railway dev environment live
- [ ] Spend Lens connection — trigger analyses, receive procurement alerts
- [x] LinkedIn marketing agent — Claude drafts, ICARUS previews, you confirm
- [ ] Agent status overview — "what are all my agents doing?" in one message

---

## Tech Stack

| Component | Tool |
|---|---|
| Bot framework | python-telegram-bot[job-queue] |
| AI — complex | Claude Sonnet (tool-use agent) |
| AI — simple | Claude Haiku (fast routing) |
| AI — images | Claude Sonnet (multimodal) |
| Voice | OpenAI Whisper API |
| Calendar | Google Calendar API |
| Email | Gmail API |
| Tasks | GitHub Issues API |
| Memory | Upstash Redis (EU West) |
| Telegram bot hosting | Railway Hobby ($5/month) — prod + dev, EU West (Amsterdam) |
| PWA hosting | Hostinger VPS (187.124.14.81) — Docker + nginx + Let's Encrypt |
| Scheduling | APScheduler via job_queue |
| PWA backend | FastAPI + uvicorn |
| PWA frontend | Vanilla JS + CSS — JARVIS HUD UI (animated SVG rings), installable PWA |
| PWA domain | icarusai.de — HTTPS, Let's Encrypt SSL auto-renewing |
