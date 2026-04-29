# Spend Lens — Agent Hierarchy

**Status:** Active  
**Parent Project:** [Spend Lens](spend-lens.md)  
**Goal:** A hierarchy of specialized AI agents, each covering a procurement domain, all reporting into Icarus (Supervisor).

---

## Architecture

```
          ┌──────────────────────────────┐
          │      ICARUS Telegram         │  ← command center, single interface
          │   (Personal + All Agents)    │
          └──────────────┬───────────────┘
                         │ reports up / receives commands
                         │
                    ┌────▼────────────────┐
                    │   Icarus Spend Lens │
                    │    (Supervisor)     │
                    │   (Orchestrator)    │
                    └──────────┬──────────┘
                               │
          ┌────────────────────┼────────────────────┐────────────────────┐
          │                    │                    │                    │
  ┌───────▼───────┐   ┌────────▼──────┐   ┌────────▼──────┐   ┌────────▼──────┐
  │   Agent 1     │   │   Agent 2     │   │   Agent 3     │   │   Agent 4     │
  │  Analytics    │   │     Risk      │   │  Compliance   │   │     RFP       │
  └───────────────┘   └───────────────┘   └───────────────┘   └───────────────┘
```

---

## Agents

### Agent 1 — Analytics
**Focus:** Spend analysis, category performance, cost trends  
**Inputs:** ERP data, spend reports, supplier invoices  
**Outputs:** Spend dashboards, savings opportunities, category benchmarks  
**Serves:** Category managers needing visibility into spend

- [ ] Define data sources
- [ ] Design analytics output format
- [ ] Build spend categorization logic
- [ ] Set up reporting cadence

---

### Agent 2 — Risk
**Focus:** Supplier risk, supply chain disruption, concentration risk  
**Inputs:** Supplier data, market signals, news feeds, financial ratings  
**Outputs:** Risk scores, alerts, mitigation recommendations  
**Serves:** Category managers and Icarus (Supervisor) for risk decisions

- [ ] Define risk scoring model
- [ ] Identify external data sources (Dun & Bradstreet, news APIs)
- [ ] Design alert thresholds
- [ ] Build escalation logic to Icarus (Supervisor)

---

### Agent 3 — Compliance
**Focus:** Policy adherence, contract compliance, regulatory requirements  
**Inputs:** Contracts, purchase orders, policy documents  
**Outputs:** Compliance flags, audit trail, remediation actions  
**Serves:** Category managers and legal/compliance teams

- [ ] Map compliance rules and policies
- [ ] Define document ingestion pipeline
- [ ] Build flag + alert system
- [ ] Design audit reporting format

---

### Agent 4 — RFP
**Focus:** RFP creation, supplier evaluation, bid analysis  
**Inputs:** Requirements docs, supplier responses, historical contracts  
**Outputs:** RFP templates, scoring matrices, supplier recommendations  
**Serves:** Category managers running sourcing events

- [ ] Build RFP template generator
- [ ] Design supplier scoring framework
- [ ] Create bid comparison logic
- [ ] Define handoff to contracting

---

## Icarus — Supervisor (Orchestrator)
**Role:** Receives consolidated reports from all 4 agents. Makes final decisions on risk, sourcing, and strategy.  
**Inputs:** Agent summaries (Analytics + Risk + Compliance + RFP)  
**Outputs:** Strategic direction, escalation decisions, category manager guidance

- [ ] Define orchestration logic (when agents trigger, how they hand off)
- [ ] Design Icarus summary report format
- [ ] Set reporting cadence (daily / weekly / on-demand)
- [ ] Build escalation rules (what triggers immediate alert vs. weekly summary)

---

## Tech Stack (Proposed)

| Component | Tool |
|-----------|------|
| Agent framework | Claude API (tool use + multi-agent) |
| Orchestration | Claude Orchestrator pattern |
| Data pipeline | Python + pandas / dbt |
| Storage | PostgreSQL or BigQuery |
| Delivery | ICARUS Telegram (primary), dashboard (secondary) |
| Scheduling | APScheduler or GitHub Actions |
