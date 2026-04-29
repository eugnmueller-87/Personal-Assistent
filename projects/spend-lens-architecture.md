# Spend Lens — Technical Architecture

**Status:** Design Phase  
**Parent Project:** [Spend Lens](spend-lens.md)  
**Goal:** Define how all agents are built, what APIs they call, how they talk to each other, and how they reach the user.

---

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER (Eugen)                             │
│              Telegram / Push Notification / Dashboard           │
└────────────────────────────┬────────────────────────────────────┘
                             │ commands / queries / reports
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    ICARUS  (Supervisor)                         │
│              Claude API — Orchestrator Agent                    │
│   • Receives triggers (scheduled or user-initiated)             │
│   • Dispatches tasks to sub-agents                              │
│   • Consolidates outputs into unified reports                   │
│   • Decides escalation vs. routine summary                      │
└──────┬──────────────┬──────────────┬──────────────┬────────────┘
       │              │              │              │
       ▼              ▼              ▼              ▼
  ┌─────────┐   ┌─────────┐   ┌──────────┐   ┌─────────┐
  │ Agent 1 │   │ Agent 2 │   │ Agent 3  │   │ Agent 4 │
  │Analytics│   │  Risk   │   │Compliance│   │   RFP   │
  └────┬────┘   └────┬────┘   └────┬─────┘   └────┬────┘
       │              │              │              │
       ▼              ▼              ▼              ▼
  ┌─────────────────────────────────────────────────────┐
  │              SPEND LENS DATA LAYER                  │
  │         PostgreSQL + File Store + Cache             │
  └─────────────────────────────────────────────────────┘
       │              │              │              │
       ▼              ▼              ▼              ▼
   ERP / CSV     D&B / News    Contracts /      RFP Docs /
   Spend Data    Feeds / APIs  Policy Docs      Supplier Data
```

---

## Core Technology

| Layer | Technology | Why |
|-------|-----------|-----|
| Agent runtime | **Claude API** (claude-sonnet-4-6) | Tool use, multi-agent, reasoning |
| Orchestration | **Claude Orchestrator pattern** | Icarus manages sub-agents natively |
| Backend | **Python + FastAPI** | Agent logic, API integrations, scheduling |
| Database | **PostgreSQL** | Structured spend, supplier, contract data |
| File storage | **AWS S3 or local** | PDFs, contracts, RFP documents |
| Scheduling | **n8n** (self-hosted) | Triggers, webhooks, workflow automation |
| User delivery | **Telegram Bot API** | Commands in, reports out — mobile-first |
| Push alerts | **Ntfy.sh** | Instant push to phone/iPad for critical alerts |
| Dashboard | **Streamlit** (Phase 2) | Visual spend views (optional, later) |

---

## Agent Specifications

### Icarus — Supervisor (Orchestrator)

**Model:** claude-sonnet-4-6  
**Trigger sources:**
- Scheduled (daily 07:00, weekly Monday)
- User message via Telegram (`/report`, `/risk`, `/status`)
- Alert escalation from sub-agents

**What it does:**
1. Receives trigger with context (what's being asked, time range, priority)
2. Decides which agents to invoke (all or selective)
3. Calls sub-agents in parallel using Claude tool use
4. Waits for all responses
5. Synthesises into a single structured report
6. Routes output: push alert (critical) or summary message (routine)
7. Sends to user via Telegram or Ntfy

**Tools available to Icarus:**
```python
tools = [
    "call_analytics_agent",    # invoke Agent 1
    "call_risk_agent",         # invoke Agent 2
    "call_compliance_agent",   # invoke Agent 3
    "call_rfp_agent",          # invoke Agent 4
    "send_telegram_message",   # deliver to user
    "send_push_notification",  # urgent alerts to phone
    "read_spend_data",         # direct DB access for context
    "create_github_issue",     # log action items to ORG-EUGEN repo
]
```

**Output format to user:**
```
📊 SPEND LENS — Daily Brief [2026-04-29]

🔴 URGENT
• Risk: Supplier X (Tier 1) flagged — financial distress signal

🟡 WATCH
• Compliance: 3 POs missing contract reference (IT category)
• Analytics: Q2 spend pace +12% vs budget

🟢 ROUTINE
• RFP: Logistics tender closes Friday — 4 bids received

[View full report] [Open issues] [Ask Icarus]
```

---

### Agent 1 — Analytics

**Model:** claude-sonnet-4-6  
**Schedule:** Daily at 06:00 (before Icarus brief)

**APIs & Data Sources:**

| Source | API / Method | Data pulled |
|--------|-------------|-------------|
| ERP system | SAP API / REST or CSV export | Purchase orders, invoices, spend by category |
| Internal DB | PostgreSQL (Spend Lens) | Historical spend, budgets, category trees |
| FX rates | **Open Exchange Rates API** (free) | Currency normalisation |
| Benchmarks | Internal targets / uploaded manually | Budget vs actual |

**What it does:**
1. Pulls latest spend data from ERP or CSV ingestion pipeline
2. Categorises spend by commodity, supplier, cost centre
3. Computes: budget vs actual, trend vs prior period, top 10 suppliers by spend
4. Flags anomalies (spend spike >20%, new uncategorised supplier)
5. Returns structured JSON to Icarus

**Output schema:**
```json
{
  "agent": "analytics",
  "period": "2026-04-W17",
  "total_spend": 1420000,
  "budget_variance": "+8.3%",
  "top_suppliers": [...],
  "anomalies": [...],
  "savings_opportunities": [...],
  "status": "yellow"
}
```

---

### Agent 2 — Risk

**Model:** claude-sonnet-4-6  
**Schedule:** Daily at 06:15

**APIs & Data Sources:**

| Source | API / Method | Data pulled |
|--------|-------------|-------------|
| Dun & Bradstreet | **D&B Direct+ API** | Supplier financial risk scores |
| News monitoring | **NewsAPI** or **GDELT** | Supplier mentions, geopolitical events |
| Financial ratings | **Refinitiv / OpenFIGI** (or manual) | Credit ratings |
| Internal DB | PostgreSQL | Supplier list, spend concentration, contracts |
| Geopolitical | **GDELT API** (free) | Country risk signals |

**What it does:**
1. Pulls supplier list from Spend Lens DB
2. Queries D&B for risk score changes on Tier 1 & 2 suppliers
3. Scans news for supplier or country risk signals
4. Computes concentration risk (% spend per supplier, per country)
5. Flags anything crossing alert thresholds
6. Returns risk summary to Icarus

**Alert thresholds:**
- 🔴 Critical: Tier 1 supplier risk score drops >10 points, bankruptcy news
- 🟡 Watch: Concentration >30% in single supplier, geopolitical event in key country
- 🟢 Routine: Minor score changes, standard monitoring

---

### Agent 3 — Compliance

**Model:** claude-sonnet-4-6  
**Schedule:** Daily at 06:30

**APIs & Data Sources:**

| Source | API / Method | Data pulled |
|--------|-------------|-------------|
| Contract store | Local file store / SharePoint API | Contract PDFs, expiry dates, terms |
| ERP | SAP API / CSV | Purchase orders, approval workflows |
| Policy docs | Internal upload (PDF → vector store) | Procurement policy rules |
| Regulatory | **EUR-Lex API** or manual | EU procurement regulations (if applicable) |

**What it does:**
1. Reads all active contracts — checks expiry within 30/60/90 days
2. Cross-checks POs against approved supplier list
3. Validates POs have contract references (flags maverick spend)
4. Checks contract value vs PO totals (over-spend alerts)
5. Scans policy rules against recent purchasing decisions
6. Returns compliance summary to Icarus

**Output includes:**
- Contracts expiring soon (with days remaining)
- POs without contract coverage
- Maverick spend percentage by category
- Any regulatory flag

---

### Agent 4 — RFP

**Model:** claude-sonnet-4-6  
**Schedule:** On-demand + weekly status check

**APIs & Data Sources:**

| Source | API / Method | Data pulled |
|--------|-------------|-------------|
| RFP document store | Local / S3 | RFP templates, active tenders, supplier responses |
| Supplier DB | PostgreSQL | Approved supplier list, past performance |
| DocuSign | **DocuSign API** (optional) | Contract signature status |
| Email | **Gmail API / Microsoft Graph** | Supplier bid submissions |

**What it does:**
1. Tracks all active RFP/tender processes with deadlines
2. Generates RFP templates from requirements (Claude text generation)
3. Ingests and parses supplier bid responses (PDF/email)
4. Scores bids against weighted criteria matrix
5. Produces supplier comparison report
6. Flags approaching deadlines to Icarus

**User-triggered actions (via Telegram):**
- `/rfp new [category]` → Icarus routes to Agent 4 → generates RFP draft
- `/rfp status` → returns all active tenders + deadlines
- `/rfp score [tender]` → runs bid scoring and returns ranking

---

## User Interaction Design

### Telegram Bot — Command Interface

The primary way you interact with the system from any device:

```
/brief          → Icarus delivers today's summary
/risk           → Agent 2 runs risk scan now
/spend [period] → Agent 1 returns spend report
/rfp status     → Agent 4 returns tender pipeline
/compliance     → Agent 3 returns compliance flags
/ask [question] → Icarus answers in natural language
```

**Example:**
```
You: /ask which supplier has the highest risk in logistics?

Icarus: Based on today's scan, TransLog GmbH (Tier 1, 
logistics) has the highest risk score at 42/100 — down 
from 61 last month. D&B flagged late payments and a 
news article reports a key contract loss. Recommend 
review within 7 days.

[Open Risk Report] [Create Action Item]
```

### Push Notifications (Ntfy)

Only critical alerts bypass Telegram:
- Supplier bankruptcy/distress signal
- Contract expired (no renewal in place)
- Spend anomaly >25% above budget
- RFP deadline in 24 hours

---

## Data Flow

```
1. INGEST       ERP export / CSV / API → Python pipeline → PostgreSQL
2. TRIGGER      n8n schedule → FastAPI endpoint → Icarus
3. DISPATCH     Icarus → calls sub-agents (parallel Claude API calls)
4. PROCESS      Each agent queries DB + external APIs → returns JSON
5. SYNTHESISE   Icarus consolidates agent outputs → formats report
6. DELIVER      Telegram message or Ntfy push → user's phone/iPad
7. LOG          Action items → GitHub Issues (ORG-EUGEN repo)
```

---

## Implementation Phases

### Phase A — Foundation (Weeks 1–2)
- [ ] Set up PostgreSQL schema (suppliers, spend, contracts, RFP)
- [ ] Build CSV / ERP ingestion pipeline
- [ ] Build Icarus skeleton (Claude API orchestrator)
- [ ] Build Telegram bot (receive commands, send messages)

### Phase B — Agents (Weeks 3–6)
- [ ] Build Agent 1 (Analytics) — spend categorisation + anomaly detection
- [ ] Build Agent 2 (Risk) — D&B integration + news monitoring
- [ ] Build Agent 3 (Compliance) — contract expiry + PO validation
- [ ] Build Agent 4 (RFP) — template generation + bid scoring

### Phase C — Integration (Weeks 7–8)
- [ ] Wire all agents through Icarus orchestration
- [ ] Set up n8n scheduling for daily triggers
- [ ] Connect Ntfy push notifications
- [ ] End-to-end test: trigger → agents → Icarus → Telegram → you

### Phase D — Refinement
- [ ] Add Streamlit dashboard (optional visual layer)
- [ ] Tune alert thresholds based on real data
- [ ] Add `/ask` natural language interface to Icarus
- [ ] Document everything for handoff / team use
