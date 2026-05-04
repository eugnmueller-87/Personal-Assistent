# TODO

> Last updated: 2026-05-02

## Now (Active)

- [ ] Add missing credentials to VPS .env — GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REFRESH_TOKEN, TAVILY_API_KEY, GOOGLE_MAPS_API_KEY, LINKEDIN_ACCESS_TOKEN, GITHUB_REPO (copy from Railway)
- [ ] Test all PWA features end-to-end with full credentials — calendar, email, search, maps, photo
- [ ] Add screenshots to repo (`screenshots/login.png`, `screenshots/chat.png`)

## Next (Queued)

- [ ] PWA push notifications — ntfy.sh or Firebase
- [ ] Weekly AI summary — Claude reviews the week, suggests priorities
- [ ] Update/close GitHub issues — edit title, body, state via conversation
- [ ] Update existing calendar events — modify time, title, location
- [ ] Personal notes — store and retrieve notes conversationally via Redis
- [ ] One-off reminders — "remind me in 2h", APScheduler + Redis

## Backlog

- [ ] Spend Lens connection — ICARUS triggers analyses, receives procurement alerts
- [ ] Voice output (TTS) — ICARUS talks back
- [ ] Google Drive access
- [ ] ICARUS desktop app — Electron or Tauri wrapping the PWA
- [ ] Wake word — "Hey ICARUS"
- [ ] n8n / Make.com automation workflows

## Done

- [x] ICARUS Telegram bot — fully operational on Railway
- [x] Google Calendar read + write
- [x] Gmail read, search, reply
- [x] GitHub Issues read + create
- [x] Web search (Tavily), Maps (Google)
- [x] Shopping list + expense tracker
- [x] LinkedIn post agent with approval flow
- [x] Morning briefing 06:00 Berlin
- [x] Proactive email alerts (15 min polling)
- [x] Persistent memory (Upstash Redis)
- [x] Sandbox environment (Railway dev + dev bot)
- [x] PWA — FastAPI backend + JARVIS HUD UI
- [x] PWA deployed to Hostinger VPS (187.124.14.81)
- [x] HTTPS via Let's Encrypt + nginx
- [x] Custom domain icarusai.de live
- [x] PWA installable on iPhone via Safari
