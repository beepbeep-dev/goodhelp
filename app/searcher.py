from ddgs import DDGS


async def search_web(query: str, num_results: int = 5) -> list[dict]:
    """Search DuckDuckGo and return a list of result URLs with titles."""
    results = []
    for r in DDGS().text(query, max_results=num_results):
        results.append({
            "title": r.get("title", ""),
            "url": r.get("href", ""),
            "snippet": r.get("body", ""),
        })
    return results
