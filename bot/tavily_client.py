import os
import requests


def web_search(query: str, max_results: int = 3) -> str:
    api_key = os.environ["TAVILY_API_KEY"]
    resp = requests.post(
        "https://api.tavily.com/search",
        json={
            "api_key": api_key,
            "query": query,
            "max_results": max_results,
            "search_depth": "basic",
            "include_answer": True,
        },
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()

    answer = data.get("answer", "").strip()
    results = data.get("results", [])

    if answer:
        return answer

    lines = []
    for r in results[:max_results]:
        title = r.get("title", "")
        content = r.get("content", "")[:300].strip()
        url = r.get("url", "")
        lines.append(f"{title}: {content} ({url})")

    return "\n\n".join(lines) if lines else "No results found."
