from urllib.parse import urljoin

from curl_cffi.requests import AsyncSession
from bs4 import BeautifulSoup


async def scrape_url(url: str) -> dict:
    async with AsyncSession() as session:
        response = await session.get(url, impersonate="chrome", timeout=15)
        response.raise_for_status()

    soup = BeautifulSoup(response.text, "lxml")

    metadata = _extract_metadata(soup, url)
    text_content = _extract_text(soup)
    links = _extract_links(soup, url)
    images = _extract_images(soup, url)

    return {
        "url": str(response.url),
        "status_code": response.status_code,
        "metadata": metadata,
        "text": text_content,
        "links": links,
        "images": images,
    }


def _extract_metadata(soup: BeautifulSoup, url: str) -> dict:
    title = soup.title.string.strip() if soup.title and soup.title.string else None

    meta_desc = soup.find("meta", attrs={"name": "description"})
    description = meta_desc["content"].strip() if meta_desc and meta_desc.get("content") else None

    meta_keywords = soup.find("meta", attrs={"name": "keywords"})
    keywords = meta_keywords["content"].strip() if meta_keywords and meta_keywords.get("content") else None

    og_tags = {}
    for tag in soup.find_all("meta", attrs={"property": lambda v: v and v.startswith("og:")}):
        key = tag["property"][3:]
        og_tags[key] = tag.get("content", "")

    canonical = soup.find("link", attrs={"rel": "canonical"})
    canonical_url = canonical["href"] if canonical and canonical.get("href") else None

    return {
        "title": title,
        "description": description,
        "keywords": keywords,
        "canonical_url": canonical_url,
        "og_tags": og_tags,
    }


def _extract_text(soup: BeautifulSoup) -> list[dict]:
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()

    blocks = []
    for el in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "td", "th", "blockquote"]):
        text = el.get_text(separator=" ", strip=True)
        if text:
            blocks.append({"tag": el.name, "text": text})

    return blocks


def _extract_links(soup: BeautifulSoup, base_url: str) -> list[dict]:
    links = []
    seen = set()
    for a in soup.find_all("a", href=True):
        href = urljoin(base_url, a["href"])
        if href in seen:
            continue
        seen.add(href)
        links.append({
            "href": href,
            "text": a.get_text(strip=True) or None,
        })
    return links


def _extract_images(soup: BeautifulSoup, base_url: str) -> list[dict]:
    images = []
    seen = set()
    for img in soup.find_all("img", src=True):
        src = urljoin(base_url, img["src"])
        if src in seen:
            continue
        seen.add(src)
        images.append({
            "src": src,
            "alt": img.get("alt", ""),
        })
    return images
