# ORG EUGEN — Handover Document
**Last updated:** 2026-04-30
**Covers:** All sessions from 2026-04-29 to present

---

## Current State — What's Live

### ICARUS Telegram Bot (@IcarusORG_bot)
Fully operational personal AI assistant. Deployed on Railway free tier, always-on.

**Repos:**
- Private (working copy): `C:\Users\eugnm\OneDrive\Desktop\ORG EUGEN\bot\`
- Public (triggers Railway deploy): `C:\Users\eugnm\OneDrive\Desktop\Personal-Assistent\bot\`
- Always mirror changes to both. Push public repo = Railway auto-redeploys.

**Live capabilities:**
| Capability | Detail |
|---|---|
| Commands | /calendar, /emails, /issues, /summary, /roadmap, /task |
| Natural language — text | Claude Sonnet 4.6 tool-use agent |
| Natural language — voice | OpenAI Whisper transcription |
| Image / document analysis | Claude multimodal — invoices, contracts, whiteboards |
| Google Calendar read | This week's events + today's events |
| Google Calendar write | Create events from voice or text, Europe/Berlin timezone |
| Gmail | Important-only, newer_than:3d default, since_minutes for time queries |
| Proactive email alerts | Every 15 min, Haiku urgency filter, deduplication via msg IDs |
| Morning briefing | 06:00 Berlin, Claude-composed, APScheduler job_queue |
| GitHub Issues | Read + create |
| Roadmap reader | Reads markdown from private ORG-EUGEN repo |
| Multi-model routing | Haiku for simple, Sonnet 4.6 for complex |
| Persistent memory | Upstash Redis — survives restarts AND redeploys |

**Environment variables (Railway — all 11 required):**
```
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
ANTHROPIC_API_KEY=
OPENAI_API_KEY=
GITHUB_TOKEN=               ← set to no expiration
GITHUB_REPO=
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REFRESH_TOKEN=
UPSTASH_REDIS_URL=
UPSTASH_REDIS_TOKEN=
```

---

## Architecture

```
ICARUS Telegram (command center — the only interface)
     │
     ├── Personal ops (live)
     │     ├── Google Calendar API (read + write)
     │     ├── Gmail API (modify scope)
     │     ├── GitHub Issues API
     │     └── Upstash Redis (persistent memory)
     │
     ├── Spend Lens agents (planned)
     │     └── Trigger analyses, receive procurement alerts
     │
     └── Marketing agent (planned)
           └── LinkedIn post drafting + publishing
```

---

## File Map

```
bot/
├── main.py           — Telegram handlers + scheduled jobs (briefing, email alerts)
├── claude_router.py  — Multi-model routing, tool-use loop, Redis memory, image analysis
├── google_client.py  — Calendar (read/write/today), Gmail (read/alerts with IDs)
├── github_client.py  — Issues, roadmap reader
└── requirements.txt  — python-telegram-bot[job-queue], anthropic, openai, upstash-redis, ...

ROADMAP.md            — Big picture vision + phase tracker
HANDOVER.md           — This file
projects/
├── icarus-bot.md         — Full ICARUS status + planned agent hub
├── spend-lens.md         — Spend Lens status + ICARUS connection plan
├── spend-lens-agents.md  — 4-agent hierarchy, connects up to ICARUS Telegram
└── org-eugen-system.md   — System overview + task tracker
```

---

## Fallback / Error Handling (as of 2026-04-30)

| Layer | Behaviour on failure |
|---|---|
| Any tool exception | `_call_tool` catches, returns error string — history stays clean |
| GitHub dict response | `get_open_issues` guards with `isinstance(issues, dict)` |
| GitHub missing `number` | `create_issue` already guarded |
| Voice handler crash | try/except in `handle_voice`, error sent to Telegram |
| Text handler crash | try/except in `handle_message`, error sent to Telegram |
| Morning briefing crash | try/except in `morning_briefing`, logged only |
| Email alert crash | try/except in `check_new_emails`, logged only |
| Redis unavailable | `_get_redis` returns None, falls back to in-memory silently |

---

## Bugs Fixed (full log)

| Bug | Cause | Fix |
|---|---|---|
| Railway vars rejected | Values had quotes (`KEY="value"`) | Remove all quotes in Raw Editor |
| Railway vars wiped on redeploy | Railway forgets | Keep local backup of all 11 vars |
| Voice handler silent failure | `route()` crashed silently | try/except around route(), surface to Telegram |
| `KeyError: 'number'` in create_issue | GitHub API returned error dict | Guard: `if "number" not in issue` |
| GitHub token expired | Default PAT expiry | Regenerated with no expiration |
| Gmail 403 accessNotConfigured | Gmail API disabled in GCP project 1098132567527 | Enabled in Cloud Console |
| Emails from 2016 | No date filter | `newer_than:3d` default + `since_minutes` param |
| `resultSizeEstimate` wildly wrong | Google's estimate is fiction | Removed, show actual count |
| Calendar write missing → `KeyError` | No calendar tool — Claude used `create_issue` instead | Added `create_calendar_event` tool |
| Credentials exposed in chat | User pasted tokens in Telegram | All credentials rotated |
| `string indices must be integers` | `get_open_issues` crashed on GitHub dict error → corrupted history → all subsequent queries fail | Fixed `get_open_issues` dict guard + wrapped `_call_tool` in try/except so tool errors never propagate |

---

## What's Next (prioritised)

1. **Email reply** — reply or archive emails directly from Telegram (gmail.modify scope already active, ~1 hour)
2. **Web search** — live data via Brave or Tavily API (~2 hours)
3. **Spend Lens connection** — ICARUS Telegram triggers Spend Lens analyses, receives alerts
4. **LinkedIn marketing agent** — Claude drafts, ICARUS previews, confirm to publish
5. **Weekly AI summary** — Claude reviews the week, suggests priorities

---

## Key Gotchas for Next Session

1. **Google OAuth must be Desktop app type** — JSON must contain `"installed"` key, not `"web"`
2. **Railway Raw Editor** — no quotes around env var values, ever
3. **Railway vars can be wiped** — always keep local backup of all 11 vars
4. **Mirror both repos** — every code change goes to ORG EUGEN bot/ AND Personal-Assistent bot/
5. **GitHub token** — set to no expiration, stored in Railway vars
6. **Upstash Redis** — free at upstash.com, 2 vars: UPSTASH_REDIS_URL + UPSTASH_REDIS_TOKEN
7. **Email filter** — tuned over 3 iterations, don't simplify: `newer_than:3d + is:important + noreply exclusions`
8. **APScheduler** — runs inside Railway via job_queue. Morning brief 06:00 Berlin. Email check every 900s (15 min).
9. **Tool errors** — `_call_tool` now catches all exceptions. Tools return error strings, not raise. History stays intact.
10. **LinkedIn API** — restrictive for posting. Evaluate n8n/Make.com as middleware before building the agent.

---

## Spend Lens — Current State

**Location:** `C:\Users\eugnm\OneDrive\Desktop\PROCUREMENT\PROCUREMENT\SpendLens_App\`
**Start:** `PYTHONUTF8=1 panel serve app.py --show --port 5006` (Git Bash)
**Stack:** Python + Panel, SQLite, Claude API (Sonnet + Haiku), 16 RSS feeds

**Live:** Full upload pipeline, dashboard, deep dive, compliance scorecard, CFO export, Icarus market intelligence agent, category strategy (7 AI frameworks + HTML export)
**Blocked:** Grok live search — code complete, needs xAI tier upgrade
**Critical path to revenue:** Security layer S1–S7 (~8 days) → pilot client €299–599/month → Q3 2026 target

---

## GitHub Repos & Profiles

| Repo | Purpose |
|---|---|
| eugnmueller-87/ORG-EUGEN (private) | Personal ops, ROADMAP, projects, HANDOVER |
| eugnmueller-87/Personal-Assistent (public) | ICARUS bot code, triggers Railway deploy |
| eugnmueller-87/eugnmueller-87 (public) | GitHub profile README |
| eugnmueller-87/PROCUREMENT (private) | Spend Lens app |
