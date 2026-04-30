import json
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

TIMEZONE = "Europe/Berlin"


def _redis():
    from claude_router import _get_redis
    return _get_redis()


# --- Shopping list ---

def get_shopping_list(user_id: str) -> list:
    r = _redis()
    if not r:
        return []
    try:
        data = r.get(f"icarus:shopping:{user_id}")
        return json.loads(data) if data else []
    except Exception as e:
        logging.warning(f"[ICARUS] shopping get failed: {e}")
        return []


def add_items(user_id: str, items: list) -> list:
    current = get_shopping_list(user_id)
    # avoid duplicates (case-insensitive)
    existing = {i.lower() for i in current}
    for item in items:
        if item.lower() not in existing:
            current.append(item)
            existing.add(item.lower())
    r = _redis()
    if r:
        try:
            r.set(f"icarus:shopping:{user_id}", json.dumps(current))
        except Exception as e:
            logging.warning(f"[ICARUS] shopping save failed: {e}")
    return current


def remove_item(user_id: str, item: str) -> list:
    current = get_shopping_list(user_id)
    updated = [i for i in current if i.lower() != item.lower()]
    r = _redis()
    if r:
        try:
            r.set(f"icarus:shopping:{user_id}", json.dumps(updated))
        except Exception as e:
            logging.warning(f"[ICARUS] shopping remove failed: {e}")
    return updated


def clear_shopping_list(user_id: str):
    r = _redis()
    if r:
        try:
            r.delete(f"icarus:shopping:{user_id}")
        except Exception as e:
            logging.warning(f"[ICARUS] shopping clear failed: {e}")


# --- Expense tracking ---

def log_expense(user_id: str, amount: float, store: str, items: str = "", currency: str = "EUR") -> str:
    r = _redis()
    if not r:
        return "Storage unavailable."
    try:
        now = datetime.now(ZoneInfo(TIMEZONE))
        entry = {
            "date": now.strftime("%Y-%m-%d"),
            "time": now.strftime("%H:%M"),
            "amount": round(amount, 2),
            "currency": currency,
            "store": store,
            "items": items,
        }
        key = f"icarus:expenses:{user_id}"
        data = r.get(key)
        expenses = json.loads(data) if data else []
        expenses.append(entry)
        r.set(key, json.dumps(expenses))
        return f"Logged: {currency} {amount:.2f} at {store} on {entry['date']}."
    except Exception as e:
        logging.warning(f"[ICARUS] expense log failed: {e}")
        return f"Failed to log expense: {e}"


def get_expenses(user_id: str, period: str = "month") -> str:
    r = _redis()
    if not r:
        return "Storage unavailable."
    try:
        data = r.get(f"icarus:expenses:{user_id}")
        if not data:
            return "No expenses logged yet."
        expenses = json.loads(data)

        now = datetime.now(ZoneInfo(TIMEZONE))
        if period == "week":
            cutoff = now.strftime("%Y-%m-%d")
            from datetime import timedelta
            cutoff_dt = now - timedelta(days=7)
            filtered = [e for e in expenses if e["date"] >= cutoff_dt.strftime("%Y-%m-%d")]
            label = "last 7 days"
        elif period == "month":
            prefix = now.strftime("%Y-%m")
            filtered = [e for e in expenses if e["date"].startswith(prefix)]
            label = now.strftime("%B %Y")
        elif period == "all":
            filtered = expenses
            label = "all time"
        else:
            filtered = expenses
            label = "all time"

        if not filtered:
            return f"No expenses in {label}."

        total = sum(e["amount"] for e in filtered)
        by_store: dict = {}
        for e in filtered:
            by_store[e["store"]] = by_store.get(e["store"], 0) + e["amount"]

        lines = [f"Expenses — {label}"]
        lines.append(f"Total: EUR {total:.2f}")
        lines.append("")
        for store, amt in sorted(by_store.items(), key=lambda x: -x[1]):
            lines.append(f"  {store}: EUR {amt:.2f}")
        lines.append("")
        for e in sorted(filtered, key=lambda x: x["date"], reverse=True)[:10]:
            item_note = f" ({e['items']})" if e["items"] else ""
            lines.append(f"  {e['date']} — EUR {e['amount']:.2f} at {e['store']}{item_note}")

        return "\n".join(lines)
    except Exception as e:
        logging.warning(f"[ICARUS] expense get failed: {e}")
        return f"Failed to get expenses: {e}"
