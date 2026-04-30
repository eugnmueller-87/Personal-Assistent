# ROADMAP — ORG EUGEN

> Big-picture vision and project trajectory. Updated as we go.

---

## Vision — ICARUS as Command Center

ICARUS Telegram is the single interface for everything. One conversation, one place.
Every agent built — personal ops, procurement AI, marketing — plugs into ICARUS.
You talk to ICARUS. ICARUS commands the agents.

```
ICARUS Telegram (the only interface you need)
     │
     ├── Personal ops        — calendar, email, tasks, memory (live)
     ├── Spend Lens agents   — trigger analyses, surface insights (planned)
     ├── Marketing agent     — draft + post LinkedIn updates (planned)
     └── Future agents       — plug in as tools, report back here
```

---

## Phase 1 — Foundation ✅

- [x] Create private GitHub repo (ORG-EUGEN)
- [x] Set up TODO.md + ROADMAP.md
- [x] Install GitHub CLI and connect account
- [x] Define all active projects in `projects/`
- [x] Establish weekly review habit (GitHub Action — auto-issue every Monday 08:00 UTC)

---

## Phase 2 — ICARUS Personal Ops ✅

- [x] Telegram bot — live, always-on (Railway free tier)
- [x] Google Calendar — read + write (natural language, voice)
- [x] Gmail — important-only filter, time-based queries, proactive alerts every 15 min
- [x] GitHub Issues — read, create, roadmap reader
- [x] Claude tool-use agent — chains tools, asks clarifying questions
- [x] Multi-model routing — Haiku for simple, Sonnet 4.6 for complex (~€4/month)
- [x] Voice messages — OpenAI Whisper, acts on spoken requests
- [x] Image/document analysis — invoices, contracts, whiteboards
- [x] Morning briefing — 06:00 Berlin, Claude-composed
- [x] Proactive email alerts — Haiku urgency filter, no spam
- [x] Persistent memory — Upstash Redis, survives restarts and redeploys

---

## Phase 3 — ICARUS Agent Hub (Next)
**Goal:** ICARUS becomes the orchestrator. Every project and agent reports here.

### Personal ops (remaining)
- [ ] Email reply — reply or archive directly from Telegram (gmail.modify scope ready)
- [ ] Web search — live data tool via Brave or Tavily API
- [ ] Weekly AI summary — Claude reviews the week, suggests priorities

### Spend Lens connection
- [ ] ICARUS can trigger a Spend Lens analysis from Telegram ("run spend analysis on last month")
- [ ] Spend Lens agents report results back to ICARUS Telegram
- [ ] Surface key procurement insights, compliance flags, and supplier alerts in Telegram
- [ ] ICARUS can create Spend Lens tasks from voice ("flag supplier X for review")

### Marketing agent
- [ ] LinkedIn post agent — Claude drafts posts about project milestones, updates, launches
- [ ] ICARUS triggers from Telegram ("post about ICARUS calendar write feature")
- [ ] Claude generates post → ICARUS previews in Telegram → confirm to publish
- [ ] Auto-post on major milestones (configurable)
- [ ] Post history tracked in GitHub Issues

---

## Phase 4 — ICARUS as Standalone App
**Goal:** ICARUS available outside Telegram — browser, desktop, mobile. Same backend, new interfaces. Build after all active projects are stable.

### PWA (web app installable on phone)
- [ ] FastAPI backend — `/chat`, `/voice`, `/photo` endpoints wrapping existing `claude_router.py`
- [ ] Chat UI — single HTML page, installable to home screen via `manifest.json`
- [ ] Voice recording via browser mic API → Whisper → same routing
- [ ] Photo upload → same `route_image()` pipeline
- [ ] PIN/password auth (replaces Telegram `CHAT_ID` guard)
- [ ] Push notifications via Firebase or similar
- [ ] Deploy to Railway alongside or instead of Telegram bot
- [ ] **Note:** `claude_router.py`, `google_client.py`, `github_client.py` — zero changes needed

### Desktop app
- [ ] Standalone desktop client for ICARUS (Electron or Tauri wrapping the PWA)
- [ ] Runs locally, no Railway dependency
- [ ] Same full feature set — calendar, email, tasks, voice, image analysis
- [ ] Windows + Mac

---

## Phase 5 — Autonomous Operations
**Goal:** The system runs mostly on its own. You review, not manage.

- [ ] Fully automated weekly/monthly reviews
- [ ] Cross-project dependency tracking (ICARUS surfaces blockers across Spend Lens + ORG EUGEN)
- [ ] Company deployment — separate Railway instance, company Google Workspace
- [ ] Agent status dashboard — one view of all active agents and their last actions
- [ ] ICARUS escalation — agents flag decisions that need human input, ICARUS queues them

---

## ICARUS — Current Capabilities (as of 2026-04-30)

| Capability | Status |
|---|---|
| Telegram commands (/calendar, /emails, /issues, /summary, /roadmap, /task) | Live |
| Natural language — text | Live |
| Natural language — voice (Whisper) | Live |
| Image / document analysis | Live |
| Google Calendar read + write | Live |
| Gmail read (important only, time-filtered) | Live |
| GitHub Issues read + create | Live |
| Roadmap reader | Live |
| Multi-model routing (Haiku + Sonnet) | Live |
| Morning briefing 06:00 Berlin | Live |
| Proactive email alerts (15 min polling) | Live |
| Persistent memory (Upstash Redis) | Live |
| Email reply from Telegram | Planned |
| Web search | Planned |
| Spend Lens agent connection | Planned |
| LinkedIn marketing agent | Planned |
| Weekly AI summary | Planned |

---

## Key Principles
1. **One interface** — ICARUS Telegram is the only place you need to go
2. **Capture everything** — one inbox, zero friction
3. **Automate the boring** — if you do it twice, automate it
4. **Ship small** — working systems beat perfect plans
5. **Agents report up** — every agent connects back to ICARUS
