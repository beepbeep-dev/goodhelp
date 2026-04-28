from urllib.parse import urlparse

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
    "t.me",
    "telegram.me",
    "discord.com",
    "discord.gg",
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

    SOURCE_LABELS = {
        "t.me": "telegram",
        "telegram.me": "telegram",
        "discord.com": "discord",
        "discord.gg": "discord",
    }

    results = []
    for r in DDGS().text(full_query, max_results=num_results):
        url = r.get("href", "")
        source = "unknown"
        for site in PASTE_SITES:
            if site in url:
                source = SOURCE_LABELS.get(site, site)
                break
        results.append({
            "title": r.get("title", ""),
            "url": url,
            "snippet": r.get("body", ""),
            "source": source,
        })
    return results


async def deep_search(query: str, num_results: int = 5, max_depth_links: int = 3) -> dict:
    """Search, scrape top results, then follow interesting links and scrape those too."""
    from app.scraper import scrape_url

    search_results = await search_web(query, num_results)

    depth_0 = []
    all_found_links = []

    for sr in search_results:
        try:
            data = await scrape_url(sr["url"])
            depth_0.append({
                "search_result": sr,
                "scrape": data,
                "error": None,
                "depth": 0,
            })
            for link in data.get("links", [])[:20]:
                href = link.get("href", "")
                if _is_interesting_link(href, sr["url"]):
                    all_found_links.append({
                        "url": href,
                        "text": link.get("text", ""),
                        "found_on": sr["url"],
                    })
        except Exception as e:
            depth_0.append({
                "search_result": sr,
                "scrape": None,
                "error": str(e),
                "depth": 0,
            })

    seen_urls = {sr["url"] for sr in search_results}
    depth_1 = []

    for link_info in all_found_links[:max_depth_links]:
        if link_info["url"] in seen_urls:
            continue
        seen_urls.add(link_info["url"])
        try:
            data = await scrape_url(link_info["url"])
            depth_1.append({
                "search_result": {
                    "title": data.get("metadata", {}).get("title", "") or link_info["text"],
                    "url": link_info["url"],
                    "snippet": f"Found on: {link_info['found_on']}",
                },
                "scrape": data,
                "error": None,
                "depth": 1,
            })
        except Exception as e:
            depth_1.append({
                "search_result": {
                    "title": link_info["text"] or link_info["url"],
                    "url": link_info["url"],
                    "snippet": f"Found on: {link_info['found_on']}",
                },
                "scrape": None,
                "error": str(e),
                "depth": 1,
            })

    return {
        "query": query,
        "results": depth_0,
        "deep_results": depth_1,
        "stats": {
            "pages_searched": num_results,
            "pages_scraped": len(depth_0),
            "links_followed": len(depth_1),
            "total_links_found": len(all_found_links),
        },
    }


def _is_interesting_link(href: str, source_url: str) -> bool:
    """Filter out junk links — keep only links to different domains with real content."""
    if not href or not href.startswith("http"):
        return False
    try:
        parsed = urlparse(href)
        source_parsed = urlparse(source_url)
    except Exception:
        return False
    if parsed.netloc == source_parsed.netloc:
        return False
    skip_domains = [
        "google.com", "facebook.com", "twitter.com", "instagram.com",
        "youtube.com", "linkedin.com", "apple.com", "microsoft.com",
        "amazon.com", "pinterest.com", "tiktok.com",
    ]
    for d in skip_domains:
        if d in parsed.netloc:
            return False
    skip_extensions = [".jpg", ".png", ".gif", ".svg", ".pdf", ".zip", ".mp4", ".mp3"]
    for ext in skip_extensions:
        if parsed.path.lower().endswith(ext):
            return False
    return True
