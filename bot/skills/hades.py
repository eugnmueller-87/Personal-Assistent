import os
import requests

_HADES_DEFAULT_URL = "https://hades-production-b86a.up.railway.app"

TOOLS = [
    {
        "name": "hades_status",
        "description": (
            "Check whether a supplier has been onboarded and due-diligenced by Hades. "
            "Use when the user asks: 'is X onboarded?', 'have we checked X?', "
            "'do we have a DD report for X?', 'is X in the system?', "
            "'has Hades investigated X?'. Returns onboarded status and latest risk verdict."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "company": {
                    "type": "string",
                    "description": "Supplier or company name to check, e.g. 'Siemens AG', 'Bosch', 'H&M Group'.",
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


def _hades_status(company: str) -> str:
    url, err = _get_url()
    if err:
        return err
    try:
        r = requests.get(f"{url}/audit/{company}/latest", timeout=10)
        if r.status_code == 404:
            return (
                f"{company} has NOT been onboarded or investigated by Hades yet.\n"
                f"To run a full DD check, say: 'Hades, investigate {company}'."
            )
        r.raise_for_status()
        record = r.json()
        date = record.get("investigated_at", "?")[:10]
        level = record.get("risk_level", "?")
        rec = record.get("recommendation", "?")
        score = record.get("overall_risk_score", "?")
        return (
            f"{company} is onboarded. Last checked: {date}\n"
            f"Risk: {_risk_badge(level)} {level} ({score}/10)  |  "
            f"Verdict: {_recommendation_badge(rec)} {rec}\n"
            f"Say 'pull the DD report for {company}' for the full breakdown."
        )
    except Exception as e:
        return f"Hades status check failed: {e}"


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
    if name == "hades_status":
        return _hades_status(inputs["company"])
    if name == "hades_report":
        return _hades_report(inputs["company"])
    if name == "hades_audit":
        return _hades_audit(inputs["company"])
    return None
