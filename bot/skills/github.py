from github_client import get_open_issues, create_issue, get_roadmap

TOOLS = [
    {
        "name": "get_issues",
        "description": "Get open GitHub issues from the user's repo.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "get_roadmap",
        "description": "Get the roadmap for a project.",
        "input_schema": {
            "type": "object",
            "properties": {
                "project": {
                    "type": "string",
                    "description": "Project name. Options: org-eugen, spendlens, icarus, agents.",
                },
            },
            "required": [],
        },
    },
    {
        "name": "create_issue",
        "description": "Create a new task or GitHub issue.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Short title of the task."},
                "body": {"type": "string", "description": "Optional description or details."},
            },
            "required": ["title"],
        },
    },
]


def handle(name: str, inputs: dict, user_id: str = "default"):
    if name == "get_issues":
        return get_open_issues()
    if name == "get_roadmap":
        return get_roadmap(inputs.get("project", "org-eugen"))
    if name == "create_issue":
        return create_issue(inputs["title"], inputs.get("body", ""))
    return None
