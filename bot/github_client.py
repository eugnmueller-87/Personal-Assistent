import os
import requests


def get_open_issues():
    token = os.environ["GITHUB_TOKEN"]
    repo = os.environ["GITHUB_REPO"]

    response = requests.get(
        f"https://api.github.com/repos/{repo}/issues",
        headers={"Authorization": f"token {token}"},
        params={"state": "open", "per_page": 10},
    )

    issues = response.json()
    if not issues:
        return "No open issues."
    if isinstance(issues, dict):
        return f"GitHub error: {issues.get('message', 'unknown error')}"

    lines = [f"Open issues ({len(issues)}):"]
    for issue in issues:
        lines.append(f"• #{issue['number']} {issue['title']}")

    return "\n".join(lines)


def create_issue(title, body=""):
    token = os.environ["GITHUB_TOKEN"]
    repo = os.environ["GITHUB_REPO"]

    response = requests.post(
        f"https://api.github.com/repos/{repo}/issues",
        headers={"Authorization": f"token {token}"},
        json={"title": title, "body": body},
    )

    issue = response.json()
    if "number" not in issue:
        return f"Failed to create issue: {issue.get('message', 'unknown error')}"
    return f"Created issue #{issue['number']}: {issue['title']}\n{issue['html_url']}"


def get_roadmap(project="org-eugen"):
    files = {
        "org-eugen": "ROADMAP.md",
        "spendlens": "projects/spend-lens.md",
        "icarus": "projects/icarus-bot.md",
        "agents": "projects/spend-lens-agents.md",
        "sandbox": "projects/icarus-sandbox-log.md",
    }

    token = os.environ["GITHUB_TOKEN"]
    repo = os.environ["GITHUB_REPO"]
    filename = files.get(project.lower(), "ROADMAP.md")

    response = requests.get(
        f"https://api.github.com/repos/{repo}/contents/{filename}",
        headers={"Authorization": f"token {token}"},
    )

    if response.status_code != 200:
        return f"Could not find roadmap for '{project}'."

    import base64
    content = base64.b64decode(response.json()["content"]).decode("utf-8")
    lines = [l for l in content.split("\n") if l.strip()]
    return "\n".join(lines[:40])
