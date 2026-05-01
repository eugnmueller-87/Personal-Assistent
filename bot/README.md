# ICARUS — Personal AI Assistant

A single-owner AI assistant that runs in Telegram and controls your personal ops stack through natural language, voice, and images.

One conversation. One place. Everything connected.

---

## What it does

- Manages your **calendar** — read, create, delete events, meeting links, attendee invites
- Manages your **email** — search, read, reply, proactive alerts for urgent messages
- Tracks **tasks and projects** via your preferred task manager
- Runs **web searches** for live information
- Finds **places and directions**
- Tracks a **shopping list and expenses** — conversational, persists across restarts
- Drafts and publishes **LinkedIn posts** with an approval step before anything goes live
- Delivers a **morning briefing** at a configured time
- **Self-heals**: exceptions trigger an automated fix proposal opened as a PR for human review

---

## Architecture

```
Telegram (the only interface)
     │
     ├── AI router
     │     ├── Lightweight model  — simple queries, urgency filtering
     │     └── Full model         — tool use, multi-step reasoning, image + voice
     │
     ├── Connected services
     │     ├── Calendar
     │     ├── Email
     │     ├── Task tracker
     │     ├── Web search
     │     └── Maps
     │
     ├── Publishing
     │     └── Social media — approval-gated before anything goes live
     │
     ├── Persistent memory        — survives restarts and redeploys
     │
     └── Self-healing
           ├── Exception → AI reads broken file → fix proposed as PR
           └── Human reviews → merge triggers redeploy
```

---

## Security

- Single owner: all handlers locked to one Telegram user ID — fail-closed on startup if not configured
- No credentials in code: all secrets via environment variables only
- Prompt injection defence: all external content is isolated before being passed to the AI
- Auto-fix denylist: core files cannot be modified by the self-healing system
- Audit log of security-relevant events with a rolling retention window

See [SECURITY.md](SECURITY.md) for the disclosure policy.

---

## Self-hosting

Clone the repo, configure your environment variables, and deploy. The bot runs on any platform that supports Python and persistent environment variables.

All credentials are loaded from environment variables at startup — nothing is hardcoded.
