# ICARUS — Personal AI Assistant

Personal AI assistant running on Telegram, powered by Claude and deployed on Railway.

## Capabilities

- Google Calendar — read and write events, Google Meet links, attendee invites
- Gmail — search, read, reply with approval flow, proactive email alerts
- GitHub Issues — read and create
- Web search via Tavily
- Google Maps — places, directions, opening hours
- Shopping list and expense tracker
- LinkedIn post drafting and publishing with approval flow
- Voice messages (OpenAI Whisper)
- Image and document analysis
- Morning briefing at 06:00 Berlin time
- Persistent memory via Upstash Redis
- Self-healing: exceptions trigger automated fix → redeploy cycle

## Stack

| Layer | Tool |
|---|---|
| Interface | Telegram Bot API |
| AI | Claude Sonnet 4.6 (complex) + Haiku 4.5 (simple) |
| Voice | OpenAI Whisper |
| Calendar / Gmail | Google APIs |
| Memory | Upstash Redis |
| Deployment | Railway |

## Access

Single-owner. All handlers are locked to the owner's Telegram user ID — the bot does not respond to anyone else.
