from shopping_client import add_items, get_shopping_list, remove_item, clear_shopping_list, log_expense, get_expenses

TOOLS = [
    {
        "name": "add_to_shopping_list",
        "description": (
            "Add one or more items to the shopping list. "
            "Use when the user mentions things to buy, says 'we need X', or 'add X to the list'. "
            "Keep collecting until the user says the list is done or goes shopping."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "items": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of items to add, e.g. ['milk', 'eggs', 'bread'].",
                },
            },
            "required": ["items"],
        },
    },
    {
        "name": "get_shopping_list",
        "description": "Show the current shopping list. Use when the user asks what's on the list.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "remove_from_shopping_list",
        "description": "Remove a single item from the shopping list. Use when the user says 'remove X' or 'got the X already'.",
        "input_schema": {
            "type": "object",
            "properties": {
                "item": {"type": "string", "description": "Item to remove."},
            },
            "required": ["item"],
        },
    },
    {
        "name": "clear_shopping_list",
        "description": "Clear the entire shopping list. Use when the user says 'shopping done', 'list complete', or 'clear the list'.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "log_expense",
        "description": (
            "Log a shopping expense. Use when the user says how much they spent, "
            "types an amount and store, or sends a receipt photo with extracted data. "
            "Always call this after reading a receipt image."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "amount": {"type": "number", "description": "Total amount spent, e.g. 45.30."},
                "store": {"type": "string", "description": "Store or merchant name, e.g. 'Rewe', 'Aldi'."},
                "items": {"type": "string", "description": "Optional: brief note on what was bought."},
                "currency": {"type": "string", "description": "Currency code. Default: EUR."},
            },
            "required": ["amount", "store"],
        },
    },
    {
        "name": "get_expenses",
        "description": (
            "Show expense summary. Use when the user asks what they spent, "
            "wants a shopping overview, or asks about spending this week or month."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "period": {
                    "type": "string",
                    "description": "Time period: 'week', 'month' (default), or 'all'.",
                },
            },
            "required": [],
        },
    },
]


def handle(name: str, inputs: dict, user_id: str = "default"):
    if name == "add_to_shopping_list":
        updated = add_items(user_id, inputs["items"])
        return f"Added. List ({len(updated)} items): {', '.join(updated)}"
    if name == "get_shopping_list":
        items = get_shopping_list(user_id)
        if not items:
            return "Shopping list is empty."
        return "Shopping list:\n" + "\n".join(f"• {i}" for i in items)
    if name == "remove_from_shopping_list":
        updated = remove_item(user_id, inputs["item"])
        return f"Removed. List ({len(updated)} items): {', '.join(updated) if updated else 'empty'}"
    if name == "clear_shopping_list":
        clear_shopping_list(user_id)
        return "Shopping list cleared."
    if name == "log_expense":
        return log_expense(
            user_id,
            inputs["amount"],
            inputs["store"],
            inputs.get("items", ""),
            inputs.get("currency", "EUR"),
        )
    if name == "get_expenses":
        return get_expenses(user_id, inputs.get("period", "month"))
    return None
