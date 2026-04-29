# ORG EUGEN — Handover Document
**Date:** 2026-04-29  
**Session:** Google Calendar API, Gmail API, Telegram bot setup, ICARUS interactive bot planning

---

## What Was Built This Session

### 1. Google Calendar + Gmail API
- **Auth script:** `workflows/gcal_auth.py`
- **Credentials:** `credentials/google_calendar.json` (Desktop app OAuth — must be Desktop app type, not Web application)
- **Token:** `credentials/token.json` (gitignored — never commit)
- **Scopes granted:**
  - `https://www.googleapis.com/auth/calendar`
  - `https://www.googleapis.com/auth/gmail.modify`
- **Python libraries installed** in SpendLens venv: `google-api-python-client`, `google-auth-httplib2`, `google-auth-oauthlib`
- **To re-authenticate:** delete `credentials/token.json` and re-run `gcal_auth.py`

### 2. Telegram Bot — @IcarusORG_bot
- **Bot name:** ICARUS
- **Username:** @IcarusORG_bot
- **Token:** stored in `.env` as `TELEGRAM_BOT_TOKEN` and as GitHub Secret
- **Chat ID:** stored in `.env` as `TELEGRAM_CHAT_ID`
- **Status:** one-way notifications working (tested — message delivered)
- **Next:** add `TELEGRAM_CHAT_ID` as GitHub Secret to enable Monday automation

### 3. Python venv
- SpendLens venv at `C:\Users\eugnm\OneDrive\Desktop\PROCUREMENT\PROCUREMENT\SpendLens_App\.venv\`
- Used for all ORG EUGEN scripts (Python 3.14)
- Run scripts with: `"C:\...\SpendLens_App\.venv\Scripts\python.exe" script.py`

---

## Planned Next — ICARUS Interactive Bot

**Goal:** Send a message to @IcarusORG_bot and get a real response (calendar, emails, GitHub issues).

**Architecture:**
- `python-telegram-bot` — bot framework
- Claude API — natural language understanding and routing
- Gmail + Calendar APIs — already authenticated
- GitHub API — already have token
- **Railway** — free hosting, always-on, deploys from GitHub repo

**Commands planned:**
- `/calendar` — this week's events
- `/emails` — unread email summary
- `/issues` — open GitHub issues
- `/summary` — everything combined
- Free text — Claude routes to the right API

**Key challenge:** Google credentials are file-based locally. Railway needs them as environment variables. Solution: extract `refresh_token` from `token.json` and store in Railway env vars.

**Files to create:**
- `bot/main.py` — bot entry point + handlers
- `bot/calendar_client.py` — Google Calendar functions
- `bot/gmail_client.py` — Gmail functions
- `requirements.txt` — bot dependencies

---

## Monday Automation (Not Yet Built)

**Goal:** Every Monday 08:00 UTC, ICARUS sends one Telegram message with:
- Link to the weekly review GitHub issue
- This week's calendar events
- Unread email count / flagged emails

**Requires:**
- GitHub Secrets: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `GOOGLE_REFRESH_TOKEN`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`
- Update `.github/workflows/weekly-review.yml` to add calendar fetch + Telegram push step

---

## Active GitHub Secrets (as of this session)
| Secret | Purpose |
|--------|---------|
| `TELEGRAM_BOT_TOKEN` | ICARUS bot token |
| `TELEGRAM_CHAT_ID` | **Still needs to be added** |

---

## Important Notes for Next Session

1. **Add `TELEGRAM_CHAT_ID` as GitHub Secret** — not done yet
2. **Desktop app credential** — when recreating OAuth, always select "Desktop app" not "Web application". The JSON must have `"installed"` at top level, not `"web"`
3. **Test users** — your Google account must be added under OAuth consent screen → Audience → Test users
4. **SpendLens venv** — use this for all ORG EUGEN Python scripts, no separate venv needed yet
5. **Railway setup** — next major step: deploy ICARUS as interactive bot
6. **Weekly review habit** — GitHub Action creates issue every Monday, bot notification not yet wired up

---

## Previous Session Summary (2026-04-29, Session 1)

### SpendLens App — Phase 0 Complete
**Location:** `C:\Users\eugnm\OneDrive\Desktop\PROCUREMENT\PROCUREMENT\SpendLens_App\`  
**Start:** `PYTHONUTF8=1 panel serve app.py --show --port 5006` (Git Bash)  
**Tech:** Python + Panel (HoloViz), SQLite, Claude API (Sonnet + Haiku), 16 RSS feeds

**Built and working:**
- Full 5-stage upload pipeline
- Dashboard (KPIs, spend evolution, budget vs actuals, health gauges)
- Deep Dive tab (treemap, supplier drill-down, risk bubbles)
- Compliance Scorecard (ABC tiers, contract status, inline editing)
- CFO Excel export
- Icarus — market intelligence agent (RSS feeds, Quick/Deep scan, Ask, RFP brief, weekly brief)
- Category Strategy tab — 7 AI frameworks + HTML slide deck export
- ECB FX rates — already implemented in `data_cleanup.py`

**Blocked:** Grok live search — code complete, needs xAI account upgrade

### Spend Lens — Next Priorities
**Immediate API integrations (free):**
1. OpenCorporates — supplier legal enrichment (~1 day)
2. Quandl / Nasdaq Data Link — commodity price context for Icarus (~2 days)

**Critical path to first revenue (Q3 2026):**
Enterprise security layer — HTTPS, encryption at rest, SSO, RBAC, audit logging, Docker packaging (~8 days total). Target: pilot client at €299–599/month.
