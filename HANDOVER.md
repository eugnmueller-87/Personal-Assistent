# ORG EUGEN — Handover Document
**Date:** 2026-04-29  
**Session:** Initial setup — repo, structure, projects, GitHub boards, Spend Lens architecture

---

## What Was Built This Session

### 1. GitHub Repository
- **Repo:** https://github.com/eugnmueller-87/ORG-EUGEN (private)
- **Local path:** `C:\Users\eugnm\OneDrive\Desktop\ORG EUGEN\`
- **Branch:** main
- **Connected via:** GitHub Desktop (GUI) — GitHub CLI not yet installed

### 2. File Structure
```
ORG EUGEN/
├── README.md                          — overview + planned stack
├── TODO.md                            — Now / Next / Backlog task list
├── ROADMAP.md                         — 4-phase plan (Foundation → Scale)
├── HANDOVER.md                        — this file
├── .env                               — API keys (gitignored, not committed)
├── .gitignore                         — protects .env and credentials/
├── projects/
│   ├── README.md                      — project index + template
│   ├── org-eugen-system.md            — this ops system tracked as a project
│   ├── spend-lens.md                  — Spend Lens main project (updated to reflect real app)
│   ├── spend-lens-agents.md           — Icarus + 4-agent hierarchy design
│   └── spend-lens-architecture.md     — full technical architecture spec
└── workflows/
    ├── README.md                      — workflow index + template
    ├── weekly-review.md               — Monday review process
    └── task-capture.md                — inbox → todo routing
```

### 3. GitHub Actions
- `.github/workflows/weekly-review.yml` — auto-creates a review issue every Monday at 08:00 UTC with a full checklist

### 4. GitHub Projects (Boards)
Two project boards created and populated:

| Board | Type | Items |
|-------|------|-------|
| ORG EUGEN | Table | 17 items across all 4 roadmap phases |
| SPENDLENS | Kanban | 19 items across Phases A–D |

**Note:** Items were added via GitHub GraphQL API using a temporary token. That token was exposed in chat and must be revoked at github.com/settings/tokens.

### 5. Environment Files
| File | Purpose | Keys added |
|------|---------|------------|
| `ORG EUGEN/.env` | ORG EUGEN automation | GITHUB_TOKEN, ANTHROPIC_API_KEY (added by user) |
| `PROCUREMENT/PROCUREMENT/SpendLens_App/.env` | SpendLens app | ANTHROPIC_API_KEY, XAI_API_KEY |

---

## Key Decisions Made

| Decision | Rationale |
|----------|-----------|
| One GitHub repo for ORG EUGEN (not multiple) | Simpler to track everything in one place at this stage |
| Kanban for SPENDLENS board | Visual task movement per agent/phase |
| Table for ORG EUGEN board | Flat list, easier to sort by priority |
| SpendLens stays in PROCUREMENT/PROCUREMENT/SpendLens_App/ | Already exists there with full history — do not move |
| No new SpendLens code created | App is already built (Phase 0 complete) — skeleton I created was deleted |
| Icarus renamed from eCaros | User clarified the name is from Greek mythology (Icarus) |
| Title changed from "Head of Procurement" to "Supervisor" | User's preference |

---

## What Already Exists (Do Not Rebuild)

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
- ECB FX rates — already implemented in `data_cleanup.py` (TODO.md is outdated on this)

**Blocked:** Grok live search — code complete, needs xAI account upgrade to grok-4 tier

---

## Active Projects in ORG EUGEN

| Project | File | Status |
|---------|------|--------|
| ORG EUGEN System | projects/org-eugen-system.md | Active |
| Spend Lens | projects/spend-lens.md | Active — Phase 0 done |
| Spend Lens Agent Hierarchy | projects/spend-lens-agents.md | Design phase |

**Other repos visible in GitHub Desktop (not yet tracked in ORG EUGEN):**
- eugnmueller-87/AI-Content-Intelligence-System
- eugnmueller-87/IRONHACK
- eugnmueller-87/PODCAST-STUDIO
- eugnmueller-87/eugnmueller-87 (profile README)

---

## Planned Stack (ORG EUGEN Automation Layer)

| Layer | Tool | Status |
|-------|------|--------|
| Task tracking | GitHub Issues + TODO.md | Live |
| Weekly review | GitHub Actions (auto-issue every Monday) | Live |
| AI agents | Claude API | Planned |
| Automation | n8n or Make.com | Planned |
| Push notifications | Ntfy.sh | Planned |
| Mobile capture | Telegram Bot | Planned |
| Calendar | Google Calendar API | Planned |
| Cloud dev | GitHub Codespaces | Planned |
| Notes sync | Obsidian + OneDrive | Planned |

---

## Spend Lens — Next Priorities

### Immediate API integrations (free)
1. **OpenCorporates** — supplier legal enrichment (jurisdiction, status, dissolved flag) — ~1 day
2. **Quandl / Nasdaq Data Link** — commodity price context for Icarus — ~2 days

### Critical path to first revenue (Q3 2026)
Enterprise security layer — ~8 days total:
- S1: HTTPS/TLS via nginx
- S2: Data encryption at rest (LUKS + SQLCipher)
- S3: SSO via Cloudflare Access or Azure AD App Proxy
- S4: Secrets out of .env (systemd or Azure Key Vault)
- S5: RBAC + SSO group mapping (Reader / Editor / Administrator)
- S6: Audit logging
- S7: Docker packaging

**Target:** One pilot client at €299–599/month by Q3 2026.

---

## Important Notes for Next Session

1. **GitHub CLI not installed** — what's installed is GitHub Desktop (GUI). CLI is at cli.github.com
2. **Token to revoke** — the token used to populate project boards was exposed in chat. Revoke at github.com/settings/tokens
3. **ECB FX is done** — already in `data_cleanup.py`, TODO.md is wrong about this
4. **SpendLens is Python 3.14** (.venv uses cpython-314) — keep in mind for any new dependencies
5. **Windows Unicode** — always start SpendLens with `PYTHONUTF8=1` on Windows for German umlaut handling
6. **Mobile work environment** — goal is to be device-agnostic (phone, iPad, laptop). GitHub Codespaces is the recommended first step
