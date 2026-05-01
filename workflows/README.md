# Workflows

Documented processes and automations. Each workflow describes a repeatable sequence of steps, who/what triggers it, and what the output is.

---

## Template

```markdown
# Workflow Name

**Trigger:** What starts this workflow  
**Owner:** Human | Agent | Automated  
**Output:** What this produces

## Steps
1. ...
2. ...

## Automations
- [ ] Not yet automated
```

---

## Active Workflows

| Workflow | Trigger | Automated |
|----------|---------|-----------|
| Weekly Review | Every Monday | No (planned) |
| Task Capture | Ad hoc | No (planned) |
| ICARUS Health Check | Every 10 min via GitHub Actions | Yes — pings `/health`, alerts Telegram on failure |
| ICARUS Self-Healing | On exception in any message or scheduled job | Yes — Claude fixes code, commits to GitHub, Railway redeploys |
