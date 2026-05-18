import os
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

_HADES_DEFAULT_URL = "https://hades-production-b86a.up.railway.app"
_SPENDLENS_DEFAULT_URL = "https://spendlens-production.up.railway.app"

TOOLS = [
    {
        "name": "hades_supplier_lookup",
        "description": (
            "Check whether a supplier is known to SpendLens (active spend data) AND "
            "whether Hades has ever run due diligence on them. Combines both checks "
            "into one answer. Use when the user asks: 'is X onboarded?', 'do we have X?', "
            "'have we checked X?', 'is X already a supplier?', 'show me the onboarding status for X', "
            "'do we have a DD report for X?', 'is X in the system?'."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "company": {
                    "type": "string",
                    "description": "Supplier or company name, e.g. 'Bechtle', 'Siemens AG', 'Bosch'.",
                },
            },
            "required": ["company"],
        },
    },
    {
        "name": "hades_report",
        "description": (
            "Pull the latest due diligence report for a supplier from Hades. "
            "Use when the user asks: 'show me the DD report for X', "
            "'pull the onboarding report for X', 'what was Hades' verdict on X?', "
            "'what is the risk score for X?', 'show me the risk breakdown for X', "
            "'what were the next steps for X?'. Returns the full latest audit record."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "company": {
                    "type": "string",
                    "description": "Supplier or company name, e.g. 'Bosch', 'Siemens AG'.",
                },
            },
            "required": ["company"],
        },
    },
    {
        "name": "hades_audit",
        "description": (
            "Get the full investigation history for a supplier — all past DD checks in chronological order. "
            "Use when the user asks: 'show me the audit trail for X', "
            "'how many times have we checked X?', 'has the risk score for X changed over time?', "
            "'show me all investigations for X', 'when was X last checked?'."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "company": {
                    "type": "string",
                    "description": "Supplier or company name.",
                },
            },
            "required": ["company"],
        },
    },
]


def _get_url() -> tuple[str, str | None]:
    raw = os.environ.get("HADES_URL", _HADES_DEFAULT_URL).strip().rstrip("/")
    if not raw.startswith("http"):
        return "", f"HADES_URL misconfigured: '{raw[:60]}'"
    return raw, None


def _get_spendlens_url() -> str:
    return os.environ.get("SPENDLENS_URL", _SPENDLENS_DEFAULT_URL).strip().rstrip("/")


def _risk_badge(level: str) -> str:
    return {"Low": "🟢", "Medium": "🟡", "High": "🔴", "Critical": "🚨"}.get(level, "⚪")


def _recommendation_badge(rec: str) -> str:
    return {"Approve": "✅", "Conditional Approval": "⚠️", "Block": "🚫"}.get(rec, "❓")


def _format_latest(record: dict) -> str:
    company = record.get("company", "?")
    score = record.get("overall_risk_score", "?")
    level = record.get("risk_level", "?")
    rec = record.get("recommendation", "?")
    date = record.get("investigated_at", "?")[:10]
    mode = record.get("mode", "full")

    lines = [
        f"Hades DD Report — {company}",
        f"Date: {date}  |  Mode: {mode}",
        f"Risk: {_risk_badge(level)} {level}  |  Score: {score}/10",
        f"Verdict: {_recommendation_badge(rec)} {rec}",
    ]

    dims = record.get("dimension_scores", {})
    if dims:
        lines.append("\nRisk breakdown:")
        dim_labels = {
            "sanctions": "Sanctions",
            "registry": "Registry",
            "news_sentiment": "News",
            "lksg_csddd": "LkSG/CSDDD",
            "esg_labour": "ESG & Labour",
            "hermes_intelligence": "Hermes Intel",
        }
        for key, label in dim_labels.items():
            val = dims.get(key)
            if val is not None:
                bar = "█" * int(val) + "░" * (10 - int(val))
                lines.append(f"  {label:<16} {bar} {val}/10")

    flags = []
    if record.get("sanctions_hit"):
        flags.append("⛔ Sanctions hit")
    if record.get("sanctions_manual_review"):
        flags.append("⚠️ Manual sanctions review required")
    lksg = record.get("lksg_signal")
    if lksg == "red_flag":
        flags.append(f"🚩 LkSG red flag ({record.get('lksg_flagged_count', '?')} findings)")
    elif lksg == "needs_monitoring":
        flags.append("🔶 LkSG: needs monitoring")
    esg = record.get("esg_rating")
    if esg == "high_risk":
        flags.append("🔴 ESG: high risk")
    if flags:
        lines.append("\nKey flags:")
        for f in flags:
            lines.append(f"  {f}")

    steps = record.get("required_next_steps", [])
    if steps:
        lines.append("\nRequired next steps:")
        for step in steps[:4]:
            lines.append(f"  • {step[:90]}")

    hermes = "Yes" if record.get("hermes_tracked") else "No"
    lines.append(f"\nHermes monitored: {hermes}")

    return "\n".join(lines)


def _fetch_hades_latest(company: str) -> dict | None:
    """Returns latest audit record dict, None if not found, raises on error."""
    url, err = _get_url()
    if err:
        raise RuntimeError(err)
    r = requests.get(f"{url}/audit/{company}/latest", timeout=10)
    if r.status_code == 404:
        return None
    r.raise_for_status()
    return r.json()


def _fetch_spendlens_vendor(company: str) -> dict | None:
    """Returns SpendLens vendor dict, None if not found, raises on error."""
    sl_url = _get_spendlens_url()
    r = requests.get(f"{sl_url}/api/suppliers/lookup/{company}", timeout=10)
    r.raise_for_status()
    data = r.json()
    return data if data.get("found") else None


def _hades_supplier_lookup(company: str) -> str:
    """Run SpendLens vendor lookup + Hades audit check in parallel, merge into one answer."""
    sl_result = None
    hades_result = None
    sl_error = None
    hades_error = None

    def fetch_sl():
        return _fetch_spendlens_vendor(company)

    def fetch_hades():
        return _fetch_hades_latest(company)

    with ThreadPoolExecutor(max_workers=2) as pool:
        sl_future = pool.submit(fetch_sl)
        hades_future = pool.submit(fetch_hades)
        for future in as_completed([sl_future, hades_future]):
            if future is sl_future:
                try:
                    sl_result = future.result()
                except Exception as e:
                    sl_error = str(e)
            else:
                try:
                    hades_result = future.result()
                except Exception as e:
                    hades_error = str(e)

    lines = [f"Supplier Status — {company}"]
    lines.append("")

    # SpendLens block
    if sl_error:
        lines.append(f"SpendLens: unavailable ({sl_error[:60]})")
    elif sl_result:
        spend = sl_result.get("total_spend_eur") or 0
        spend_str = f"€{spend/1000:.1f}M" if spend >= 1000 else f"€{spend:,.0f}"
        cat = sl_result.get("category") or "unknown category"
        last = sl_result.get("last_seen") or "?"
        txn = sl_result.get("transaction_count") or 0
        country = sl_result.get("country") or ""
        country_str = f" ({country})" if country else ""
        single = " ⚠️ Single source" if sl_result.get("single_source") else ""
        lines.append(f"SpendLens: ✅ Active supplier{country_str}")
        lines.append(f"  Category: {cat}{single}")
        lines.append(f"  Spend: {spend_str}  |  {txn} transactions  |  Last seen: {last}")
    else:
        lines.append(f"SpendLens: ❌ Not in spend data — no transactions recorded for '{company}'")

    lines.append("")

    # Hades block
    if hades_error:
        lines.append(f"Hades DD: unavailable ({hades_error[:60]})")
    elif hades_result:
        date = hades_result.get("investigated_at", "?")[:10]
        level = hades_result.get("risk_level", "?")
        rec = hades_result.get("recommendation", "?")
        score = hades_result.get("overall_risk_score", "?")
        lksg = hades_result.get("lksg_signal") or ""
        lksg_str = f"  |  LkSG: {lksg}" if lksg else ""
        lines.append(f"Hades DD: ✅ Investigated — last checked {date}")
        lines.append(
            f"  Risk: {_risk_badge(level)} {level} ({score}/10)  |  "
            f"Verdict: {_recommendation_badge(rec)} {rec}{lksg_str}"
        )
        lines.append(f"  Say 'pull the DD report for {company}' for full breakdown.")
    else:
        lines.append("Hades DD: ❌ Not yet investigated")
        lines.append(f"  → Say 'investigate {company}' to run a full DD check.")

    return "\n".join(lines)


def _hades_report(company: str) -> str:
    url, err = _get_url()
    if err:
        return err
    try:
        r = requests.get(f"{url}/audit/{company}/latest", timeout=10)
        if r.status_code == 404:
            return (
                f"No DD report found for {company}.\n"
                f"To run one, say: 'Hades, investigate {company}'."
            )
        r.raise_for_status()
        return _format_latest(r.json())
    except Exception as e:
        return f"Hades report failed: {e}"


def _hades_audit(company: str) -> str:
    url, err = _get_url()
    if err:
        return err
    try:
        r = requests.get(f"{url}/audit/{company}", timeout=10)
        r.raise_for_status()
        data = r.json()
        history = data.get("history", [])
        count = data.get("investigation_count", 0)
        if not history:
            return (
                f"No audit records found for {company}.\n"
                f"To run a DD check, say: 'Hades, investigate {company}'."
            )
        lines = [f"Hades audit trail — {company} ({count} investigation{'s' if count != 1 else ''}):"]
        for i, record in enumerate(history, 1):
            date = record.get("investigated_at", "?")[:10]
            mode = record.get("mode", "full")
            score = record.get("overall_risk_score", "?")
            level = record.get("risk_level", "?")
            rec = record.get("recommendation", "?")
            lines.append(
                f"\n#{i}  {date}  [{mode}]  "
                f"{_risk_badge(level)} {level} {score}/10  "
                f"{_recommendation_badge(rec)} {rec}"
            )
            lksg = record.get("lksg_signal")
            if lksg:
                lines.append(f"     LkSG: {lksg}")
        return "\n".join(lines)
    except Exception as e:
        return f"Hades audit failed: {e}"


def handle(name: str, inputs: dict, user_id: str = "default"):
    if name == "hades_supplier_lookup":
        return _hades_supplier_lookup(inputs["company"])
    if name == "hades_report":
        return _hades_report(inputs["company"])
    if name == "hades_audit":
        return _hades_audit(inputs["company"])
    return None
