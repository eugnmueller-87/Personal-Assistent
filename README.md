# ORG EUGEN

Personal operations system — todos, projects, workflows, and automation.

## Structure

```
ORG-EUGEN/
├── README.md               — this file
├── TODO.md                 — active task list (Now / Next / Backlog)
├── ROADMAP.md              — big-picture phases and goals
├── HANDOVER.md             — session handover notes
├── projects/               — one file per project
├── workflows/              — documented and automated processes
│   ├── gcal_auth.py        — Google Calendar + Gmail OAuth setup
│   └── weekly-review.md    — Monday review process
└── credentials/            — OAuth tokens (gitignored, never committed)
```

## Quick Links
- [TODO.md](TODO.md) — what needs doing
- [ROADMAP.md](ROADMAP.md) — where we're going
- [Active Projects](projects/README.md)
- [Workflows](workflows/README.md)

## Roadmaps
| Project | Roadmap | Status |
|---------|---------|--------|
| ORG EUGEN | [ROADMAP.md](ROADMAP.md) | Phase 2 complete, Phase 3 in progress |
| SpendLens | [projects/spend-lens.md](projects/spend-lens.md) | Phase 0 complete, Phase A next |
| SpendLens Agents | [projects/spend-lens-agents.md](projects/spend-lens-agents.md) | Design phase |
| ICARUS Bot | [projects/icarus-bot.md](projects/icarus-bot.md) | Live — Phase 3 personal ops mostly done |

## Stack
| Layer | Tool | Status |
|-------|------|--------|
| Task tracking | GitHub Issues + TODO.md | Live |
| Weekly review | GitHub Actions (Monday 08:00 UTC) | Live |
| ICARUS — interactive AI assistant | Telegram bot on Railway Hobby ($5/month) | Live |
| Natural language + voice + images | Claude Sonnet 4.6 + Haiku 4.5 + Whisper | Live |
| Google Calendar | Google Calendar API (read + write) | Live |
| Gmail | Gmail API — read, search, full body, reply | Live |
| GitHub Issues | GitHub API — read + create | Live |
| Roadmap reader | GitHub API — reads any project markdown | Live |
| Web search | Tavily API | Live |
| Google Maps | Places API + Directions API | Live |
| Shopping list | Conversational — add/remove/clear, Redis-backed | Live |
| Expense tracker | Log by text or receipt photo — weekly/monthly summary | Live |
| LinkedIn posts | Draft, preview, Post/Edit/Cancel approval flow from Telegram | Live |
| Morning briefing | 06:00 Berlin, Claude-composed from calendar + email + issues | Live |
| Proactive email alerts | Polls every 15 min, AI urgency filter, no spam | Live |
| Multi-model routing | Haiku for simple, Sonnet for complex — auto-selected | Live |
| Persistent memory | Upstash Redis (EU West) | Live |
| Sandbox environment | icarus-dev on Railway — dev branch, isolated Redis namespace | Live |
| PWA — ICARUS web app | JARVIS-style chat UI, PIN auth, voice, photo — installable on mobile | Live (SANDBOX/dev) |
| Health monitoring | GitHub Actions cron + `/health` endpoint — Telegram alert if bot is down | Live |
| Self-healing | Exception → fix proposal → human review → redeploy | Live |
| Automation | n8n / Make.com | Planned |
| Whiteboard | Excalidraw / Miro | Planned |
