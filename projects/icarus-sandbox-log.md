# ICARUS Sandbox — Test & Audit Log

**Environment:** icarus-dev (Railway, EU West Amsterdam)
**Bot:** @IcarusORG_dev_bot
**Branch:** dev
**Redis prefix:** `icarus:dev:*`
**Isolation:** separate bot token, separate Redis namespace, no LinkedIn token

---

## How to Use This Log

Before merging any `dev` feature to `main`:
1. Run through the relevant test cases below
2. Mark each with ✅ pass / ❌ fail / ⚠️ partial
3. Add an entry to the Deployment Audit at the bottom

---

## Test Checklist

### Core messaging
| # | Test | Expected | Result | Date |
|---|------|----------|--------|------|
| T01 | Send `/start` | ICARUS online message | | |
| T02 | Send plain text message | Claude responds | | |
| T03 | Send voice message | Transcription + response | | |
| T04 | Send photo (not receipt) | Image analysis response | | |
| T05 | Send receipt photo | Auto-logs expense, confirms | | |

### Calendar
| # | Test | Expected | Result | Date |
|---|------|----------|--------|------|
| T10 | `/calendar` | This week's events | | |
| T11 | "Create meeting tomorrow 3pm" | Event created, asks remote/in-person | | |
| T12 | "Create call with Stefan tomorrow" | Asks for email + remote/in-person | | |

### Email
| # | Test | Expected | Result | Date |
|---|------|----------|--------|------|
| T20 | `/emails` | Unread inbox summary | | |
| T21 | "Any emails from [name]?" | search_emails called | | |
| T22 | "Show me the email" | get_email_body called, content shown | | |
| T23 | "Reply to [name]" | Draft staged, Send/Edit/Cancel buttons appear | | |
| T24 | Confirm send on staged reply | Reply sent | | |
| T25 | Edit staged reply | Edit mode active, new draft accepted | | |
| T26 | Cancel staged reply | Reply cleared | | |

### GitHub
| # | Test | Expected | Result | Date |
|---|------|----------|--------|------|
| T30 | `/issues` | Open issues listed | | |
| T31 | `/task Test task title` | Issue created, URL returned | | |
| T32 | `/roadmap icarus` | icarus-bot.md content returned | | |

### Shopping & Expenses
| # | Test | Expected | Result | Date |
|---|------|----------|--------|------|
| T40 | "Add milk and bread to shopping list" | Items added, list returned | | |
| T41 | "Remove milk from list" | Item removed | | |
| T42 | "Clear shopping list" | List cleared | | |
| T43 | "I spent €23 at Rewe" | Expense logged | | |
| T44 | "Show my expenses this month" | Summary by store | | |

### LinkedIn
| # | Test | Expected | Result | Date |
|---|------|----------|--------|------|
| T50 | "Write a LinkedIn post about X" | Draft shown, Post/Edit/Cancel buttons | | |
| T51 | Confirm post — dev has no LinkedIn token | Should fail gracefully (no token) | | |

### Web & Maps
| # | Test | Expected | Result | Date |
|---|------|----------|--------|------|
| T60 | "What's the weather in Berlin?" | Web search called, answer returned | | |
| T61 | "Find a sushi restaurant near Mitte" | Maps results returned | | |

### Redis isolation check
| # | Test | Expected | Result | Date |
|---|------|----------|--------|------|
| T70 | Log expense in dev, check prod | Expense NOT visible in prod bot | | |
| T71 | Add shopping item in dev, check prod | Item NOT visible in prod bot | | |

### Audit log
| # | Test | Expected | Result | Date |
|---|------|----------|--------|------|
| T80 | `/audit` | Last 20 events shown | | |

---

## Deployment Audit

| Date | Branch commit | What was deployed | Tested by | Notes |
|------|--------------|-------------------|-----------|-------|
| 2026-05-02 | 51cbcb1 | Redis namespace isolation (`redis_ns.py`) — all 5 files updated | Eugen | Initial sandbox setup |
| 2026-05-02 | 9da8882 | Roadmap updates — sandbox docs, EU region, Hobby plan | Eugen | Docs only, no functional change |

---

## Known Issues / Open Items

| # | Issue | Severity | Status |
|---|-------|----------|--------|
| I01 | LinkedIn post confirm will fail in dev (no token) — by design | Low | Expected |
| I02 | CI not yet running on `dev` branch | Medium | Open |
