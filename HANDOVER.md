# ORG EUGEN — Handover Document
**Last updated:** 2026-05-01
**Covers:** All sessions from 2026-04-29 to present

---

## Current State — What's Live

### ICARUS Telegram Bot (@IcarusORG_bot)
Fully operational personal AI assistant. Deployed on Railway free tier, always-on.

**Repos:**
- Working copy: `C:\Users\eugnm\OneDrive\Desktop\ORG EUGEN\bot\`
- Railway deploy trigger: `eugnmueller-87/Personal-Assistent` (push here = redeploy)
- Mirror changes to both: `git push origin main && git push railway main --force`

**Live capabilities:**
| Capability | Detail |
|---|---|
| Commands | /calendar, /emails, /issues, /summary, /roadmap, /task |
| Natural language — text | Claude Sonnet 4.6 tool-use agent |
| Natural language — voice | OpenAI Whisper transcription |
| Image / document analysis | Claude multimodal — invoices, contracts, whiteboards |
| Google Calendar read | This week's events + today's events |
| Google Calendar write | Create events — start/end time, recurrence, timezone |
| Calendar — attendees | Email invites sent automatically via `sendUpdates="all"` |
| Calendar — Google Meet | `add_meet=true` generates Meet link via conferenceData |
| Calendar — location | In-person events get a location field |
| Calendar — find & delete | Find events by title, delete by ID |
| Gmail | Important-only, newer_than:3d default, since_minutes for time queries |
| Gmail — email body | Full plain-text body fetch by message ID |
| Gmail — search | By sender, subject, keyword, sent mail |
| Proactive email alerts | Every 15 min, Haiku urgency filter, deduplication via msg IDs |
| Morning briefing | 06:00 Berlin, Claude-composed, APScheduler job_queue |
| GitHub Issues | Read + create |
| Roadmap reader | Reads markdown from private ORG-EUGEN repo |
| Web search | Live data via Tavily API |
| Google Maps | Places API + Directions API |
| Shopping list | Add items, log expenses with amounts |
| LinkedIn posting | Drafts post, stages for approval, Post/Edit/Cancel buttons |
| LinkedIn @mentions | `@Ironhack` auto-converts to LTF tag (urn:li:organization:3297892) |
| Self-healing | Errors trigger auto-fix via Claude → GitHub commit → Railway redeploy |
| Multi-model routing | Haiku for simple, Sonnet 4.6 for complex |
| Persistent memory | Upstash Redis — survives restarts AND redeploys |

**Environment variables (Railway — all required):**
```
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
ANTHROPIC_API_KEY=
OPENAI_API_KEY=
GITHUB_TOKEN=               ← set to no expiration, workflow scope required
GITHUB_REPO=
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REFRESH_TOKEN=
UPSTASH_REDIS_URL=
UPSTASH_REDIS_TOKEN=
TAVILY_API_KEY=
GOOGLE_MAPS_API_KEY=
LINKEDIN_ACCESS_TOKEN=
RAILWAY_REPO=eugnmueller-87/Personal-Assistent   ← used by auto_debug
```

---

## Architecture

```
ICARUS Telegram (command center — the only interface)
     │
     ├── Personal ops (live)
     │     ├── Google Calendar API (read + write + invites + Meet)
     │     ├── Gmail API (modify scope — read, search, body, reply)
     │     ├── GitHub Issues API
     │     ├── Tavily web search
     │     ├── Google Maps API
     │     └── Upstash Redis (persistent memory)
     │
     ├── LinkedIn (live)
     │     ├── Posts API + LTF (real @mentions)
     │     └── Approval flow before any post goes live
     │
     ├── Self-healing (live)
     │     ├── auto_debug.py catches exceptions
     │     ├── Claude Sonnet reads + fixes the broken file
     │     ├── GitHub API commits the fix
     │     └── Railway auto-redeploys → Redis flag → startup success report
     │
     └── Spend Lens agents (planned)
           └── Trigger analyses, receive procurement alerts
```

---

## File Map

```
bot/
├── main.py              — Telegram handlers, scheduled jobs, LinkedIn approval flow
├── claude_router.py     — Multi-model routing, tool-use loop, Redis memory, image analysis
├── google_client.py     — Calendar (read/write/invites/meet/find/delete), Gmail
├── github_client.py     — Issues, roadmap reader
├── linkedin_client.py   — Posts API + LTF, KNOWN_MENTIONS, stage/confirm/edit flow
├── auto_debug.py        — Self-healing: catch error → Claude fix → GitHub commit → redeploy
├── skills/
│   ├── __init__.py      — Aggregates all skill modules
│   ├── calendar.py      — Calendar tool definitions + handler
│   ├── email.py         — Gmail tool definitions + handler
│   ├── github.py        — GitHub tool definitions + handler
│   ├── maps.py          — Maps tool definitions + handler
│   ├── search.py        — Web search tool definition + handler
│   ├── shopping.py      — Shopping list + expense tracker tools
│   └── linkedin.py      — LinkedIn post_to_linkedin tool + handler
├── LINKEDIN_API_NOTES.md — LTF docs, URN formats, KNOWN_MENTIONS guide
└── requirements.txt

ROADMAP.md       — Big picture vision + phase tracker
HANDOVER.md      — This file
projects/
├── icarus-bot.md
├── spend-lens.md
├── spend-lens-agents.md
└── org-eugen-system.md
```

---

## LinkedIn Setup

**API:** Posts API (`/rest/posts`) with Little Text Format (LTF)
**Why not UGC API:** Old endpoint treats @mentions as literal text — no real tagging
**Mentions:** `KNOWN_MENTIONS` dict in `linkedin_client.py` maps lowercase name → URN

**Current known mentions:**
```python
KNOWN_MENTIONS = {
    "ironhack": "urn:li:organization:3297892",
}
```

**To add a new mention target:**
1. Open LinkedIn page → DevTools Console → `allow pasting` → run:
   ```javascript
   const csrf = document.cookie.match(/JSESSIONID="?([^";]+)/)?.[1];
   fetch('/voyager/api/organization/companies?q=universalName&universalName=SLUG', {headers:{'csrf-token':csrf,'x-restli-protocol-version':'2.0.0'}}).then(r=>r.text()).then(t=>console.log(t.match(/urn:li:\w+:\d+/g)))
   ```
   Where SLUG is the company's URL name (e.g. `ironhack` from `linkedin.com/school/ironhack`)
2. Add to `KNOWN_MENTIONS` and push to both remotes

**Limitation:** Arbitrary @mentions (any name, resolved live) require LinkedIn Marketing Developer Platform — not available on personal apps.

---

## Self-Healing System

`auto_debug.py` — fully automated error recovery:

1. Any exception in `handle_message`, `handle_voice`, or `handle_photo` → caught
2. `handle_error(exc, tb_str)` extracts the failing file path from the traceback
3. Reads the file from GitHub API
4. Sends code + error to Claude Sonnet with fix prompt
5. Commits the fixed file back to GitHub via GitHub API
6. Sets Redis key `icarus:pending_fix` (TTL 10 min)
7. Railway auto-redeploys from the new commit
8. On next startup, `check_pending_fix()` reads the Redis flag and sends success report to Telegram

**Required env var:** `RAILWAY_REPO=eugnmueller-87/Personal-Assistent` (no hardcoded fallback)
**Max attempts:** 2 per file per session

---

## Fallback / Error Handling

| Layer | Behaviour on failure |
|---|---|
| Any tool exception | `_call_tool` catches, returns error string — history stays clean |
| GitHub dict response | `get_open_issues` guards with `isinstance(issues, dict)` |
| Slash commands | try/except per command, error sent to Telegram |
| /summary — individual API failure | Each of three APIs wrapped separately |
| Voice / photo / text handlers | try/except, surfaces to Telegram + triggers auto_debug |
| Morning briefing crash | try/except, logged only |
| Email alert crash | try/except, logged only |
| Redis unavailable | Falls back to in-memory silently |

---

## Bugs Fixed (full log)

| Bug | Cause | Fix |
|---|---|---|
| Railway vars rejected | Values had quotes (`KEY="value"`) | Remove all quotes in Raw Editor |
| Railway vars wiped on redeploy | Railway forgets | Keep local backup of all vars |
| Voice handler silent failure | `route()` crashed silently | try/except around route(), surface to Telegram |
| `KeyError: 'number'` in create_issue | GitHub API returned error dict | Guard: `if "number" not in issue` |
| GitHub token expired | Default PAT expiry | Regenerated with no expiration |
| Gmail 403 accessNotConfigured | Gmail API disabled in GCP | Enabled in Cloud Console |
| Emails from 2016 | No date filter | `newer_than:3d` default |
| Calendar write missing | No tool — Claude used create_issue instead | Added create_calendar_event |
| Credentials exposed in chat | User pasted tokens in Telegram | All credentials rotated |
| `string indices must be integers` | get_open_issues crashed → corrupted history | Fixed dict guard + wrapped _call_tool |
| Slash commands crashed silently | No try/except in handlers | All slash commands wrapped |
| Voice silent failure on Whisper error | try/finally (no except) | Changed to try/except/finally |
| LinkedIn posts not formatting | Markdown in posts | Enforced plain text in system prompt |
| LinkedIn @mentions not resolving | UGC API treats them as literal text | Migrated to Posts API + LTF |
| auto_debug hardcoded repo name | Security — repo name visible in public code | Now reads from RAILWAY_REPO env var only |
| Push to railway rejected | PAT missing `workflow` scope | User updated PAT scope |

---

## Key Gotchas for Next Session

1. **Google OAuth must be Desktop app type** — JSON must contain `"installed"` key, not `"web"`
2. **Railway Raw Editor** — no quotes around env var values, ever
3. **Railway vars can be wiped** — always keep local backup of all vars
4. **Push to both remotes** — `git push origin main && git push railway main --force`
5. **GitHub PAT** — needs `workflow` scope (for Actions files), no expiration
6. **Upstash Redis** — free at upstash.com, 2 vars: UPSTASH_REDIS_URL + UPSTASH_REDIS_TOKEN
7. **Email filter** — tuned over 3 iterations, don't simplify
8. **APScheduler** — morning brief 06:00 Berlin, email check every 900s
9. **Tool errors** — `_call_tool` catches all exceptions, returns error strings, never raises
10. **LinkedIn API** — Posts API only (not UGC). LTF for @mentions. No live mention resolution without Marketing API.
11. **RAILWAY_REPO env var** — must be set in Railway for self-healing to work
12. **LinkedIn KNOWN_MENTIONS** — only fixed entities work. Adding new ones requires finding URN via DevTools.

---

## What's Next (prioritised)

1. **Email reply** — reply or archive directly from Telegram (gmail.modify scope already active)
2. **Spend Lens connection** — ICARUS triggers Spend Lens analyses, receives procurement alerts
3. **Weekly AI summary** — Claude reviews the week, suggests priorities

### Backlog
4. **ICARUS PWA** — FastAPI backend + installable web UI. `claude_router.py` unchanged.
5. **ICARUS desktop app** — Electron or Tauri wrapping the PWA.

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
