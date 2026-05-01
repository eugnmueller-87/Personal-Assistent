# Security Policy

## Overview

ICARUS is a single-owner personal AI assistant. Only one Telegram user ID is authorised to interact with it. This policy covers responsible disclosure for anyone who finds a security issue in the public codebase.

## Supported Versions

Only the latest commit on `main` is maintained and supported.

| Branch | Supported |
|--------|-----------|
| `main` (latest) | Yes |
| Any older commit | No |

## Security Controls in Place

| Control | Implementation |
|---|---|
| Owner-only access | All Telegram handlers locked to a single `CHAT_ID` via `filters.User` — fail-closed on startup if not set |
| No credentials in code | All secrets loaded from environment variables only; nothing hardcoded |
| Prompt injection defence | All external data (emails, web search, GitHub content) wrapped in `[UNTRUSTED EXTERNAL DATA]` tags before being passed to Claude |
| Auto-fix denylist | Core files (`main.py`, `claude_router.py`, `auto_debug.py`, all clients) cannot be modified by the self-healing system |
| Audit log | Security-relevant events (tool calls, auth failures, auto-fix triggers) logged to Redis with a 100-entry rolling window |
| Self-healing review gate | Auto-fix proposals open a GitHub PR for human review — never merge automatically |
| .gitignore | Screenshots, session notes, OAuth helper scripts, and credential files are excluded from version control |

## Reporting a Vulnerability

If you find a security issue in this codebase, please **do not open a public GitHub issue**.

Report privately by email: **eugnmueller@googlemail.com**

Include:
- A description of the vulnerability
- Steps to reproduce or a proof-of-concept
- Potential impact

You can expect an acknowledgement within 72 hours. There is no bug bounty programme — this is a personal project.

## Scope

**In scope:**
- Authentication bypass (Telegram user ID check)
- Prompt injection via external data sources (Gmail, GitHub, web search)
- Secrets leakage from the codebase or logs
- Self-healing system writing malicious code via the auto-fix pipeline
- Dependency vulnerabilities with a realistic attack path

**Out of scope:**
- Attacks requiring physical access to the deployment server
- Telegram platform vulnerabilities (report to Telegram directly)
- Google / Anthropic / Railway API vulnerabilities (report to those vendors)
- Theoretical issues with no realistic exploit path against a single-user bot

## Dependencies

Key runtime dependencies and their roles:

| Package | Role |
|---|---|
| `python-telegram-bot` | Telegram interface |
| `anthropic` | Claude API (Sonnet 4.6 + Haiku 4.5) |
| `openai` | Whisper voice transcription |
| `google-api-python-client` | Calendar and Gmail APIs |
| `upstash-redis` | Persistent memory and audit log |
| `requests` | GitHub API, self-healing, Maps API |

Dependencies are pinned in `requirements.txt`. Update regularly and check with `pip-audit` or GitHub Dependabot.
