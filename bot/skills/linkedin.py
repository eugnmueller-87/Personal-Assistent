from linkedin_client import post_to_linkedin

TOOLS = [
    {
        "name": "post_to_linkedin",
        "description": (
            "Draft and post a message to LinkedIn. "
            "Use when the user asks to post, share, or publish something on LinkedIn. "
            "Always show the draft to the user for approval before posting — "
            "unless the user explicitly says 'post it' or 'publish now'. "
            "Format the draft with proper line breaks between each point. "
            "No markdown, no ---, no ** or __. Plain text only."
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
        return post_to_linkedin(inputs["text"])
    return None
