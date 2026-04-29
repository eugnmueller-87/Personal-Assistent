# Spend Lens

**Status:** Active  
**Started:** 2026-04-29  
**Goal:** Build an AI-powered spend analysis platform with an agent hierarchy that serves category managers and reports into the Head of Procurement.

## Overview

Spend Lens is the main procurement intelligence project. It uses a multi-agent architecture where specialized agents handle distinct procurement domains and funnel insights up to the Head of Procurement (eCaros).

## Sub-Projects

| Sub-Project | File | Status |
|-------------|------|--------|
| Agent Hierarchy | [spend-lens-agents.md](spend-lens-agents.md) | Active |

## Tasks

- [ ] Define data sources (ERP, contracts, supplier data)
- [ ] Map spend categories and commodity structure
- [ ] Design agent input/output schema
- [ ] Build agent hierarchy (see sub-project)
- [ ] Define reporting cadence to eCaros
- [ ] Set up category manager access / delivery format

## Notes

- Agents report into **eCaros** (Head of Procurement)
- Each agent covers a separate procurement commodity / domain
- Output format for category managers TBD (dashboard / report / Slack / email)
