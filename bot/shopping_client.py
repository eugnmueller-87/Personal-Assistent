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

def _store_emoji(store: str) -> str:
    w = store.lower()
    if any(k in w for k in ["restaurant","café","cafe","pizza","burger","sushi","bistro","bar","grill","ristorante","küche","kitchen"]):
        return "🍽️"
    if any(k in w for k in ["tankstelle","shell","aral","bp","total","esso"]):
        return "⛽"
    if any(k in w for k in ["apotheke","pharmacy"]):
        return "💊"
    if any(k in w for k in ["rewe","aldi","lidl","edeka","kaufland","penny","netto","spar","alnatura","bio"]):
        return "🏪"
    return "🛍️"


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
        item_note = f" — {items}" if items else ""
        return f"✅ {_store_emoji(store)} {store} · {currency} {amount:.2f}{item_note}"
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
            from datetime import timedelta
            cutoff_dt = now - timedelta(days=7)
            filtered = [e for e in expenses if e["date"] >= cutoff_dt.strftime("%Y-%m-%d")]
            label = "Last 7 days"
        elif period == "month":
            prefix = now.strftime("%Y-%m")
            filtered = [e for e in expenses if e["date"].startswith(prefix)]
            label = now.strftime("%B %Y")
        elif period == "all":
            filtered = expenses
            label = "All time"
        else:
            filtered = expenses
            label = "All time"

        if not filtered:
            return f"No expenses in {label.lower()}."

        total = sum(e["amount"] for e in filtered)
        by_store: dict = {}
        for e in filtered:
            by_store[e["store"]] = by_store.get(e["store"], 0) + e["amount"]

        lines = [f"💶 {label} — EUR {total:.2f}", ""]
        for store, amt in sorted(by_store.items(), key=lambda x: -x[1]):
            lines.append(f"{_store_emoji(store)} {store} · EUR {amt:.2f}")
        lines.append("")
        lines.append("─────────────────")
        for e in sorted(filtered, key=lambda x: x["date"], reverse=True)[:10]:
            item_note = f"  ({e['items']})" if e["items"] else ""
            date_short = e["date"][5:]  # MM-DD
            lines.append(f"{date_short}  {e['store']}  EUR {e['amount']:.2f}{item_note}")

        return "\n".join(lines)
    except Exception as e:
        logging.warning(f"[ICARUS] expense get failed: {e}")
        return f"Failed to get expenses: {e}"
