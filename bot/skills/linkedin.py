from linkedin_client import stage_linkedin_post

TOOLS = [
    {
        "name": "post_to_linkedin",
        "description": (
            "Stage a LinkedIn post for user approval. "
            "Use when the user asks to post, share, or publish something on LinkedIn. "
            "This stages the post — the user must approve via buttons before it goes live. "
            "Format with proper line breaks between each point. "
            "No markdown, no ---, no ** or __. Plain text only. "
            "Hashtags go on their own line at the very end."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "The full text of the LinkedIn post.",
                },
            },
            "required": ["text"],
        },
    },
]


def handle(name: str, inputs: dict, user_id: str = "default"):
    if name == "post_to_linkedin":
        return stage_linkedin_post(user_id, inputs["text"])
    return None
