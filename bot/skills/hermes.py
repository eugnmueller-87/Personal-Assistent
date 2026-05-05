import os
import requests

_HERMES_DEFAULT_URL = "https://hermes-agent-production-114e.up.railway.app"
_HERMES_DEFAULT_KEY = "hermes-icarus-2026"

HERMES_API_KEY = os.environ.get("HERMES_API_KEY", _HERMES_DEFAULT_KEY)

TOOLS = [
    {
        "name": "hermes_chart",
        "description": (
            "Generate an inline chart image from Hermes market intelligence data. "
            "Use when the user asks for a chart, graph, visual, or wants to see signals visualised. "
            "Returns a PNG image URL that Icarus will send as a photo in Telegram."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "chart_type": {
                    "type": "string",
                    "enum": ["signals", "landscape"],
                    "description": (
                        "signals = bar chart of significant signals by urgency (HIGH/MEDIUM/LOW). "
                        "Best for: 'what's urgent?', 'show me what's critical', 'how many high signals?', "
                        "'what's moving today', urgency or priority questions. "
                        "landscape = horizontal bar chart of item counts per category (top 10). "
                        "Best for: 'what sectors have most activity?', 'overview by category', "
                        "'which markets are most covered?', 'show me the landscape', category or coverage questions."
                    ),
                },
            },
            "required": ["chart_type"],
        },
    },
    {
        "name": "hermes_query",
        "description": (
            "Query Hermes market intelligence for a specific company or supplier. "
            "Use when the user asks what Hermes has on a company, wants recent signals "
            "for a supplier, or asks about market news for a specific company."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "company": {
                    "type": "string",
                    "description": "Company name to look up, e.g. 'NVIDIA', 'TSMC', 'OpenAI'.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max signals to return. Default 5.",
                },
            },
            "required": ["company"],
        },
    },
    {
        "name": "hermes_greet",
        "description": (
            "Ask Hermes to introduce himself and share his current status. "
            "Use when the user asks Icarus to greet Hermes, check if Hermes is alive, "
            "or wants to know what Hermes is currently tracking."
        ),
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "hermes_search",
        "description": (
            "Search Hermes market intelligence by topic, theme, or natural language query. "
            "Use when the user asks about a theme, trend, or topic across multiple suppliers — "
            "e.g. 'any signals about chip shortages?', 'what are cloud suppliers saying about pricing?', "
            "'supply chain disruptions this week', 'AI compute capacity'. "
            "Use hermes_query for a specific named company. Use hermes_search for topics and themes."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Natural language topic or theme to search for across all suppliers.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max results to return. Default 10.",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "hermes_crawl",
        "description": (
            "Tell Hermes to run an immediate crawl cycle to collect fresh market intelligence. "
            "Use when the user asks Hermes to crawl, run a crawl, fetch fresh data, update signals, "
            "or collect new intelligence. Crawler types: 'rss' (news feeds, runs in minutes) or "
            "'edgar' (SEC filings, runs in minutes). Default to 'rss' if not specified."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "crawler": {
                    "type": "string",
                    "enum": ["rss", "edgar", "tavily", "jobs", "transcripts"],
                    "description": (
                        "Which crawler to run: "
                        "'rss' for news feeds, "
                        "'edgar' for SEC filings, "
                        "'tavily' for deep web search, "
                        "'jobs' for job postings (hiring signals), "
                        "'transcripts' for earnings call 8-K filings."
                    ),
                },
            },
            "required": ["crawler"],
        },
    },
    {
        "name": "hermes_digest",
        "description": (
            "Get the weekly Hermes market intelligence digest — a Claude-written summary "
            "of the most significant signals per category for the current week. "
            "Use when the user asks for a weekly digest, weekly summary, weekly report, "
            "'what happened this week in the market?', or 'give me the weekly Hermes report'."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "refresh": {
                    "type": "boolean",
                    "description": "Force regeneration of the digest. Default false.",
                },
            },
            "required": [],
        },
    },
    {
        "name": "hermes_watch",
        "description": (
            "Manage the Hermes supplier watchlist — companies that get crawled every 2 hours "
            "instead of every 6 hours. "
            "Use when the user says 'watch X closely', 'add X to watchlist', "
            "'stop watching X', 'remove X from watchlist', or 'show me the watchlist'."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["add", "remove", "list"],
                    "description": "'add' to watch a company, 'remove' to unwatch, 'list' to see all watched companies.",
                },
                "company": {
                    "type": "string",
                    "description": "Company name — required for add/remove, omit for list.",
                },
            },
            "required": ["action"],
        },
    },
    {
        "name": "hermes_delta",
        "description": (
            "Compare this week's macro themes to last week's — what's new, what's continuing, "
            "what has faded. Use when the user asks 'what changed this week?', "
            "'what's new vs last week?', 'any new trends?', 'what themes are continuing?'."
        ),
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "hermes_enrich",
        "description": (
            "Ask Hermes to enrich a company profile — extract key products, pricing notes, "
            "and a risk summary from accumulated signals using Claude Haiku. "
            "Use when the user asks 'enrich the profile for X', 'extract key products for Y', "
            "'what are Z's key products?', or 'summarise the risk for W'."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "company": {
                    "type": "string",
                    "description": "Company to enrich.",
                },
            },
            "required": ["company"],
        },
    },
    {
        "name": "hermes_trends",
        "description": (
            "Get macro theme clusters detected across all recent Hermes signals. "
            "Use when the user asks about emerging trends, patterns, or macro themes — "
            "'what themes are emerging this week?', 'what macro trends do you see?', "
            "'any patterns across suppliers?', 'what are the big stories right now?'. "
            "Returns clusters of signals grouped by theme with a synthesis for each."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "refresh": {
                    "type": "boolean",
                    "description": "Force a fresh cluster rebuild instead of using the cached result. Default false.",
                },
            },
            "required": [],
        },
    },
    {
        "name": "hermes_profile",
        "description": (
            "Get the accumulated knowledge profile for a specific company — "
            "not just recent signals but everything Hermes has learned over time: "
            "signal counts, urgency breakdown, top signal types, risk flags, recent history. "
            "Use when the user asks 'what do we know about X?', 'full profile on Y', "
            "'tell me about Z', 'how much have we tracked on W?'."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "company": {
                    "type": "string",
                    "description": "Company name to retrieve profile for, e.g. 'TSMC', 'Cerebras', 'OpenAI'.",
                },
            },
            "required": ["company"],
        },
    },
    {
        "name": "hermes_briefing",
        "description": (
            "Get the latest significant market intelligence signals from Hermes "
            "across all tracked suppliers. Use when the user asks for a Hermes briefing, "
            "market overview, top signals, or what's moving in the market today."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Max signals to return. Default 10.",
                },
            },
            "required": [],
        },
    },
]


def _get_url() -> tuple[str, str | None]:
    """Returns (url, error). Error is set if URL is missing or malformed."""
    raw = os.environ.get("HERMES_URL", _HERMES_DEFAULT_URL).strip().strip('"').strip("'").rstrip("/")
    if not raw:
        return "", "HERMES_URL is not set in environment."
    if not raw.startswith("http"):
        return "", f"HERMES_URL is misconfigured (got: '{raw[:60]}') — must start with https://"
    return raw, None


def _headers():
    return {"x-api-key": HERMES_API_KEY} if HERMES_API_KEY else {}


def _format_item(item: dict) -> str:
    emoji = item.get("emoji", "📰")
    urgency = item.get("urgency", "")
    supplier = item.get("supplier", "")
    title = item.get("title", "")[:120]
    date = item.get("published", "")[:10]
    reason = item.get("significance_reason", "")
    line = f"{emoji} [{urgency}] {supplier} — {title} ({date})"
    if reason:
        line += f"\n   {reason[:120]}"
    return line


def _hermes_digest(refresh: bool = False) -> str:
    url, err = _get_url()
    if err:
        return err
    try:
        params = {"refresh": "true"} if refresh else {}
        r = requests.get(f"{url}/digest", params=params, headers=_headers(), timeout=60)
        r.raise_for_status()
        data = r.json()
        if data.get("status") == "regenerating":
            return data["message"]
        digest = data.get("digest")
        if not digest:
            return data.get("message", "No weekly digest available yet.")
        lines = [
            f"Weekly digest — {digest.get('week', '')} "
            f"({digest.get('total_signals', '?')} signals processed)"
        ]
        lines.append(f"\nOverall: {digest.get('overall', '')}")
        for cat in digest.get("categories", []):
            lines.append(f"\n{cat['name']} ({cat['signal_count']} signals)")
            lines.append(f"  {cat['summary']}")
            if cat.get("top_signal"):
                lines.append(f"  Top: {cat['top_signal']}")
        return "\n".join(lines)
    except Exception as e:
        return f"Hermes digest failed: {e}"


def _hermes_watch(action: str, company: str = "") -> str:
    url, err = _get_url()
    if err:
        return err
    try:
        if action == "list":
            r = requests.get(f"{url}/watchlist", headers=_headers(), timeout=10)
            r.raise_for_status()
            data = r.json()
            slugs = data.get("watchlist", [])
            if not slugs:
                return "Watchlist is empty. Say 'watch [company] closely' to add one."
            names = ", ".join(s.replace("_", " ").title() for s in slugs)
            return f"Watchlist ({len(slugs)} companies): {names}\nThese are crawled every 2 hours."
        if not company:
            return "Please specify a company name."
        if action == "add":
            r = requests.post(f"{url}/watchlist/{company}", headers=_headers(), timeout=10)
            r.raise_for_status()
            return f"{company} added to watchlist — will now be crawled every 2 hours."
        if action == "remove":
            r = requests.delete(f"{url}/watchlist/{company}", headers=_headers(), timeout=10)
            r.raise_for_status()
            return f"{company} removed from watchlist."
        return f"Unknown action: {action}"
    except Exception as e:
        return f"Hermes watchlist failed: {e}"


def _hermes_delta() -> str:
    url, err = _get_url()
    if err:
        return err
    try:
        r = requests.get(f"{url}/trends/delta", headers=_headers(), timeout=20)
        r.raise_for_status()
        data = r.json()
        if not data.get("has_history"):
            return "No last-week data yet — trend comparison will be available after the first full week."
        lines = [
            f"Trend delta — week {data['week']} "
            f"(this week: {data['this_week_clusters']} themes, last week: {data['last_week_clusters']})"
        ]
        if data.get("new"):
            lines.append(f"\nNew this week ({len(data['new'])}):")
            for c in data["new"]:
                lines.append(f"  🆕 {c['label']}")
        if data.get("continuing"):
            lines.append(f"\nContinuing ({len(data['continuing'])}):")
            for c in data["continuing"]:
                lines.append(f"  🔄 {c['label']}")
        if data.get("resolved"):
            lines.append(f"\nFaded since last week ({len(data['resolved'])}):")
            for c in data["resolved"]:
                lines.append(f"  ✅ {c['label']}")
        return "\n".join(lines)
    except Exception as e:
        return f"Hermes delta failed: {e}"


def _hermes_enrich(company: str) -> str:
    url, err = _get_url()
    if err:
        return err
    try:
        r = requests.post(f"{url}/enrich/{company}", headers=_headers(), timeout=30)
        r.raise_for_status()
        data = r.json()
        profile = data.get("profile", {})
        lines = [f"Enriched: {data.get('company', company)}"]
        if profile.get("key_products"):
            lines.append(f"Key products: {', '.join(profile['key_products'])}")
        if profile.get("pricing_notes"):
            lines.append(f"Pricing: {profile['pricing_notes']}")
        if profile.get("risk_summary"):
            lines.append(f"Risk: {profile['risk_summary']}")
        return "\n".join(lines)
    except Exception as e:
        return f"Hermes enrich failed: {e}"


def _hermes_trends(refresh: bool = False) -> str:
    url, err = _get_url()
    if err:
        return err
    try:
        params = {"refresh": "true"} if refresh else {}
        r = requests.get(f"{url}/clusters", params=params, headers=_headers(), timeout=45)
        r.raise_for_status()
        data = r.json()
        clusters = data.get("clusters", [])
        if not clusters:
            return "No macro clusters detected yet — needs more significant signals. Try running a crawl first."
        cached_note = " (cached)" if data.get("cached") else " (fresh)"
        lines = [f"Hermes macro trends{cached_note} — {len(clusters)} clusters:"]
        for i, cluster in enumerate(clusters, 1):
            companies = ", ".join(cluster.get("companies", []))
            urg = cluster.get("urgency", {})
            urg_str = f"🔴{urg.get('HIGH', 0)} 🟡{urg.get('MEDIUM', 0)} 🟢{urg.get('LOW', 0)}"
            lines.append(f"\n{i}. {cluster['label']}  [{urg_str}]")
            lines.append(f"   {cluster['synthesis']}")
            lines.append(f"   Companies: {companies}")
        return "\n".join(lines)
    except Exception as e:
        return f"Hermes trends failed: {e}"


def _hermes_profile(company: str) -> str:
    url, err = _get_url()
    if err:
        return err
    try:
        r = requests.get(f"{url}/profile/{company}", headers=_headers(), timeout=15)
        r.raise_for_status()
        data = r.json()
        profile = data.get("profile")
        if not profile:
            return data.get("message", f"No profile for {company} yet.")
        lines = [f"Profile: {data['company']}"]
        cat = profile.get("category", "")
        tier = profile.get("tier", "")
        if cat or tier:
            lines.append(f"Category: {cat}  |  Tier {tier}")
        lines.append(
            f"Signals: {profile['total_signals']} total, {profile['significant_signals']} significant"
        )
        lines.append(
            f"First seen: {profile.get('first_seen', '—')[:10]}  |  "
            f"Last updated: {profile.get('last_updated', '—')[:10]}"
        )
        urg = profile.get("urgency_counts", {})
        lines.append(
            f"Urgency: 🔴 {urg.get('HIGH', 0)} HIGH · "
            f"🟡 {urg.get('MEDIUM', 0)} MEDIUM · "
            f"🟢 {urg.get('LOW', 0)} LOW"
        )
        sig_types = sorted(
            profile.get("signal_type_counts", {}).items(), key=lambda x: x[1], reverse=True
        )[:3]
        if sig_types:
            lines.append(f"Top signal types: {', '.join(f'{k} ({v})' for k, v in sig_types)}")
        if profile.get("risk_flags"):
            lines.append("\nRisk flags:")
            for flag in profile["risk_flags"][:3]:
                lines.append(f"  ⚠️ {flag['title'][:80]}  ({flag['published'][:10]})")
                if flag.get("reason"):
                    lines.append(f"     {flag['reason'][:120]}")
        if profile.get("recent_signals"):
            lines.append("\nRecent signals:")
            emo = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}
            for sig in profile["recent_signals"][:5]:
                e = emo.get(sig.get("urgency", ""), "📰")
                lines.append(f"  {e} {sig['title'][:80]}  ({sig['published'][:10]})")
        return "\n".join(lines)
    except Exception as e:
        return f"Hermes profile failed: {e}"


def _hermes_chart(chart_type: str) -> str:
    url, err = _get_url()
    if err:
        return err
    endpoint = "signals" if chart_type == "signals" else "landscape"
    try:
        r = requests.get(f"{url}/chart/{endpoint}", headers=_headers(), timeout=30)
        r.raise_for_status()
        chart_url = r.json()["url"]
        return f"Chart ready: {chart_url}"
    except Exception as e:
        return f"Hermes chart failed: {e}"


def _hermes_query(company: str, limit: int = 5) -> str:
    url, err = _get_url()
    if err:
        return err
    try:
        r = requests.get(f"{url}/query/{company}", params={"limit": limit}, headers=_headers(), timeout=15)
        r.raise_for_status()
        data = r.json()
        signals = data.get("signals", [])
        if not signals:
            return data.get("message", f"No signals found for {company}.")
        lines = [f"Hermes — {data['company']} ({len(signals)} signals):"]
        for item in signals:
            lines.append(_format_item(item))
        return "\n".join(lines)
    except Exception as e:
        return f"Hermes query failed: {e}"


def _hermes_briefing(limit: int = 10) -> str:
    url, err = _get_url()
    if err:
        return err
    try:
        r = requests.get(f"{url}/briefing", params={"limit": limit}, headers=_headers(), timeout=15)
        r.raise_for_status()
        data = r.json()
        signals = data.get("signals", [])
        if not signals:
            return "No significant Hermes signals yet — data accumulates as crawlers run."
        lines = [f"Hermes briefing — top {len(signals)} signals:"]
        for item in signals:
            lines.append(_format_item(item))
        return "\n".join(lines)
    except Exception as e:
        return f"Hermes briefing failed: {e}"


def _hermes_search(query: str, limit: int = 10) -> str:
    url, err = _get_url()
    if err:
        return err
    try:
        r = requests.get(f"{url}/search", params={"q": query, "limit": limit}, headers=_headers(), timeout=20)
        r.raise_for_status()
        data = r.json()
        results = data.get("results", [])
        if not results:
            return f"No Hermes signals matched '{query}' — try a broader topic or trigger a crawl first."
        lines = [f"Hermes search — '{query}' ({len(results)} results):"]
        for item in results:
            score = item.get("_score", "")
            score_str = f" [{score}]" if score else ""
            lines.append(_format_item(item) + score_str)
        return "\n".join(lines)
    except Exception as e:
        return f"Hermes search failed: {e}"


def _hermes_crawl(crawler: str = "rss") -> str:
    url, err = _get_url()
    if err:
        return err
    try:
        r = requests.post(f"{url}/crawl/{crawler}", headers=_headers(), timeout=15)
        r.raise_for_status()
        return f"Hermes started a {crawler.upper()} crawl cycle. Results will be stored in Redis within a few minutes."
    except Exception as e:
        return f"Hermes crawl trigger failed: {e}"


def _hermes_greet() -> str:
    url, err = _get_url()
    if err:
        return err
    try:
        r = requests.get(f"{url}/greet", timeout=10)
        r.raise_for_status()
        data = r.json()
        return f"{data['message']}\n\n{data['latest']}"
    except Exception as e:
        return f"Hermes did not respond: {e}"


def handle(name: str, inputs: dict, user_id: str = "default"):
    if name == "hermes_greet":
        return _hermes_greet()
    if name == "hermes_chart":
        return _hermes_chart(inputs.get("chart_type", "signals"))
    if name == "hermes_query":
        return _hermes_query(inputs["company"], inputs.get("limit", 5))
    if name == "hermes_digest":
        return _hermes_digest(inputs.get("refresh", False))
    if name == "hermes_watch":
        return _hermes_watch(inputs["action"], inputs.get("company", ""))
    if name == "hermes_delta":
        return _hermes_delta()
    if name == "hermes_enrich":
        return _hermes_enrich(inputs["company"])
    if name == "hermes_trends":
        return _hermes_trends(inputs.get("refresh", False))
    if name == "hermes_profile":
        return _hermes_profile(inputs["company"])
    if name == "hermes_briefing":
        return _hermes_briefing(inputs.get("limit", 10))
    if name == "hermes_search":
        return _hermes_search(inputs["query"], inputs.get("limit", 10))
    if name == "hermes_crawl":
        return _hermes_crawl(inputs.get("crawler", "rss"))
    return None
