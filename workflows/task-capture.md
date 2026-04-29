# Task Capture

**Trigger:** Any new idea, task, or obligation  
**Owner:** Human (to be automated via Telegram bot)  
**Output:** New item in TODO.md or GitHub Issue

## Steps
1. Capture the raw thought (voice, text, message)
2. Decide: is it a task, a project, or reference material?
3. Add to the right place:
   - Task → TODO.md (Now / Next / Backlog)
   - Project → new file in `projects/`
   - Reference → `notes/` (planned)
4. Assign priority and rough timeline

## Automations (planned)
- [ ] Telegram bot: send message → auto-creates GitHub Issue
- [ ] GitHub Issue labels: `now`, `next`, `backlog`, `project`
- [ ] Claude agent: classify and route incoming captures automatically
