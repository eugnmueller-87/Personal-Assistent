# ROADMAP — ORG EUGEN

> Big-picture vision and project trajectory. Updated as we go.

---

## Phase 1 — Foundation ✅
**Goal:** Get the basics in place so nothing falls through the cracks.

- [x] Create private GitHub repo (ORG-EUGEN)
- [x] Set up TODO.md + ROADMAP.md
- [x] Install GitHub CLI and connect account
- [x] Define all active projects in `projects/`
- [x] Establish weekly review habit (GitHub Action — auto-issue every Monday 08:00 UTC)

---

## Phase 2 — Automation + Mobility Layer ✅ (mostly done)
**Goal:** Reduce manual work, get notified on what matters, work from anywhere.

- [x] Telegram bot (@IcarusORG_bot) — live, one-way notifications
- [x] Google Calendar API — read + write (OAuth, Europe/Berlin timezone)
- [x] Gmail API — connected (modify scope, important-only filter, time-based queries)
- [x] ICARUS interactive bot — deployed on Railway (always-on, free tier)
- [x] Claude tool-use agent — ICARUS decides which tools to call, chains multiple tools, asks clarifying questions
- [x] Multi-model routing — Haiku for simple commands, Sonnet 4.6 for complex reasoning (~€4/month)
- [x] Voice messages — OpenAI Whisper transcription, acts on spoken requests
- [x] Image/document analysis — send any photo, Claude extracts key info (invoices, contracts, whiteboards)
- [x] Calendar write — create events from natural language or voice
- [x] Conversation memory — per-session context (resets on restart)
- [ ] Morning briefing — daily 08:00 push: calendar + emails + open tasks
- [ ] Proactive email alerts — notify when flagged emails arrive
- [ ] n8n / Make.com automation workflows
- [ ] Mobilized work environment — device-agnostic setup
- [ ] Cloud dev environment (GitHub Codespaces or similar)
- [ ] Synced notes + docs across all devices

---

## Phase 3 — Agent Layer (Next)
**Goal:** ICARUS gets smarter, more proactive, and survives restarts.

- [ ] Persistent memory — conversation history survives Railway restarts (SQLite or file)
- [ ] Email reply — reply or archive emails directly from Telegram (gmail.modify scope ready)
- [ ] Web search — live data tool (prices, news, weather) via Brave or Tavily API
- [ ] Proactive alerts — poll Gmail every 15 min, push Telegram on important new email
- [ ] Weekly AI summary — Claude summarizes the week and suggests priorities
- [ ] Whiteboard agent (Miro/Excalidraw API)
- [ ] Multi-agent orchestration (Claude tool use)

---

## Phase 4 — Scale (4–6 months)
**Goal:** The system works mostly on its own.

- [ ] Fully automated weekly/monthly reviews
- [ ] Cross-project dependency tracking
- [ ] Dashboard (Notion or custom web app)
- [ ] Company deployment — separate Railway instance with company Google Workspace credentials
- [ ] Team onboarding (if applicable)

---

## ICARUS — Current Capabilities (as of 2026-04-29)

| Capability | Status |
|---|---|
| Telegram commands (/calendar, /emails, /issues, /summary, /roadmap, /task) | Live |
| Natural language — text | Live |
| Natural language — voice (Whisper) | Live |
| Image / document analysis | Live |
| Google Calendar read | Live |
| Google Calendar write | Live |
| Gmail read (important only, last 3 days default) | Live |
| GitHub Issues read + create | Live |
| Roadmap reader | Live |
| Multi-model routing (Haiku + Sonnet) | Live |
| Conversation memory (session) | Live |
| Persistent memory (across restarts) | Planned |
| Email reply | Planned |
| Web search | Planned |
| Morning briefing | Planned |
| Proactive email alerts | Planned |

---

## Key Principles
1. **Capture everything** — one inbox, zero friction
2. **Review regularly** — weekly at minimum
3. **Automate the boring** — if you do it twice, automate it
4. **Ship small** — working systems beat perfect plans
5. **Work from anywhere** — no task or tool should require a specific machine
