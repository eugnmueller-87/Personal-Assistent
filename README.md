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
| ORG EUGEN | [ROADMAP.md](ROADMAP.md) | Phase 1 complete, Phase 2 in progress |
| SpendLens | [projects/spend-lens.md](projects/spend-lens.md) | Phase 0 complete, Phase A next |
| SpendLens Agents | [projects/spend-lens-agents.md](projects/spend-lens-agents.md) | Design phase |
| ICARUS Bot | [projects/icarus-bot.md](projects/icarus-bot.md) | Phase A next — Railway deploy |

## Stack
| Layer | Tool | Status |
|-------|------|--------|
| Task tracking | GitHub Issues + TODO.md | Live |
| Weekly review | GitHub Actions (Monday 08:00 UTC) | Live |
| AI assistant | Claude API | Live |
| Google Calendar | Google Calendar API (OAuth) | Live |
| Gmail | Gmail API (modify scope) | Live |
| Telegram bot | @IcarusORG_bot | Live — one-way notifications |
| Interactive bot | ICARUS on Railway | Planned |
| Automation | n8n / Make.com | Planned |
| Whiteboard | Excalidraw / Miro | Planned |
