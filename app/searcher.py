from ddgs import DDGS

PASTE_SITES = [
    "pastebin.com",
    "rentry.co",
    "dpaste.org",
    "paste.ee",
    "hastebin.com",
    "ghostbin.me",
    "paste.mozilla.org",
    "ideone.com",
    "paste.centos.org",
    "bpa.st",
]


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


async def search_pastes(query: str, num_results: int = 10) -> list[dict]:
    """Search paste sites via DuckDuckGo for pastes matching keywords."""
    site_filter = " OR ".join(f"site:{s}" for s in PASTE_SITES)
    full_query = f"{query} ({site_filter})"

    results = []
    for r in DDGS().text(full_query, max_results=num_results):
        url = r.get("href", "")
        source = "unknown"
        for site in PASTE_SITES:
            if site in url:
                source = site
                break
        results.append({
            "title": r.get("title", ""),
            "url": url,
            "snippet": r.get("body", ""),
            "source": source,
        })
    return results
