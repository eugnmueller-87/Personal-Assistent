# Spend Lens

**Status:** Active  
**Location:** `PROCUREMENT/PROCUREMENT/SpendLens_App/`  
**GitHub:** eugnmueller-87/PROCUREMENT  
**Started:** 2026 (prototype complete)  
**Goal:** AI-powered procurement intelligence platform — mid-market SaaS targeting companies with €10M–500M annual spend.

## What Already Exists (Phase 0 — Complete)

| Component | Status |
|-----------|--------|
| Upload pipeline (5 stages: map → clean → categorise → flag → store) | ✅ Live |
| Dashboard — KPIs, spend evolution, budget vs actuals, health gauges | ✅ Live |
| Deep Dive — treemap, supplier drill-down, Capex/Opex, risk bubbles | ✅ Live |
| Compliance Scorecard — ABC tiers, contract status, inline editing | ✅ Live |
| CFO Excel export | ✅ Live |
| Icarus — market intelligence agent (16 RSS feeds, Quick/Deep scan) | ✅ Live |
| Icarus — Ask / RFP brief / weekly intelligence brief | ✅ Live |
| Icarus — Grok live search (code complete, blocked on xAI tier upgrade) | 🔨 Blocked |
| Category Strategy — 7 AI frameworks (Kraljic, PESTEL, SWOT, Porter's, TCO, Levers, Recommendation) | ✅ Live |
| Category Strategy — HTML slide deck export | ✅ Live |

## Tech Stack (Actual)

| Layer | Technology |
|-------|-----------|
| UI | Python + Panel (HoloViz) |
| Agent | Claude API (claude-sonnet + haiku) |
| Database | SQLite (WAL mode) — spendlens.db + icarus_memory.db |
| Market signals | RSS (16 feeds) + xAI Grok (pending tier upgrade) |
| Start command | `PYTHONUTF8=1 panel serve app.py --show --port 5006` |

## Sub-Projects

| Sub-Project | File | Status |
|-------------|------|--------|
| Agent Hierarchy (Icarus + 4 sub-agents) | [spend-lens-agents.md](spend-lens-agents.md) | Planned |
| Technical Architecture | [spend-lens-architecture.md](spend-lens-architecture.md) | Design phase |

## Next Priorities (from TODO.md)

### Immediate
- [ ] ECB FX rates — multi-currency → EUR conversion (`data_cleanup.py`) — ~1 day
- [ ] OpenCorporates — supplier legal enrichment (free tier) — ~1 day
- [ ] Quandl / Nasdaq Data Link — commodity price context for Icarus — ~2 days
- [ ] User profiles + RBAC (Reader / Editor / Administrator) — ~3 days

### Critical Path to First Revenue (Q3 2026)
- [ ] Enterprise security S1–S7 (~8 days total):
  - S1: HTTPS/TLS via nginx
  - S2: Data encryption at rest (LUKS + SQLCipher)
  - S3: SSO via identity-aware proxy (Cloudflare Access / Azure AD)
  - S4: Secrets management (out of .env)
  - S5: RBAC + SSO group mapping
  - S6: Audit logging
  - S7: Docker packaging
- [ ] Sign first pilot contract (€299–599/month)
- [ ] Data Processing Agreement (DPA) template

## Commercial Roadmap

| Phase | Target | Revenue |
|-------|--------|---------|
| 0 — Prototype | Now ✅ | €0 |
| 1 — First client | Q3 2026 | €299–599/mo |
| 2 — Pilot SaaS | Q4 2026–Q1 2027 | €900–3,000/mo |
| 3 — Commercial SaaS | Q2–Q3 2027 | €8,000–16,000/mo |
| 4 — Enterprise | 2028+ | €55,000–90,000/mo |

**Critical path:** Security layer (S1–S7, ~8 days) → one pilot client signed.

## Notes
- Start app: `PYTHONUTF8=1 panel serve app.py --show --port 5006` (Git Bash, from SpendLens_App/)
- `PYTHONUTF8=1` required on Windows for German umlauts
- xAI Grok live search blocked until account upgraded to grok-4 tier
- Icarus feedback learning loop partially wired — needs end-to-end test
