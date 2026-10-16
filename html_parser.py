"""
HTML parser module.
Extracts title, meta tags, headings, paragraphs, links, and cleaned text from raw HTML.
"""

from typing import Any
from bs4 import BeautifulSoup


def parse_html(html: str, page_url: str) -> dict[str, Any]:
    """
    Extract title, metadata, headings, paragraphs, links,
    and readable clean text from HTML content.
    """
    soup = BeautifulSoup(html, "html.parser")

    # Title extraction
    title = ""
    if soup.title and soup.title.string:
        title = soup.title.get_text(" ", strip=True)
    elif soup.find("meta", property="og:title"):
        title = soup.find("meta", property="og:title").get("content", "").strip()

    # Meta description
    meta_desc = ""
    desc_tag = soup.find("meta", attrs={"name": "description"}) or soup.find(
        "meta", property="og:description"
    )
    if desc_tag and desc_tag.get("content"):
        meta_desc = desc_tag["content"].strip()

    # Collect links before decomposing elements
    raw_links = []
    for anchor in soup.find_all("a", href=True):
        href = anchor.get("href", "").strip()
        link_text = anchor.get_text(" ", strip=True)
        if href and not href.startswith(("javascript:", "mailto:", "tel:", "#")):
            raw_links.append({
                "text": link_text,
                "href": href,
            })

    # Remove non-content elements
    for element in soup(["script", "style", "noscript", "svg", "template", "iframe"]):
        element.decompose()

    # Headings
    headings = [
        heading.get_text(" ", strip=True)
        for heading in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"])
        if heading.get_text(" ", strip=True)
    ]

    # Paragraphs
    paragraphs = [
        p.get_text(" ", strip=True)
        for p in soup.find_all("p")
        if p.get_text(" ", strip=True)
    ]

    # Clean textual body
    clean_text = soup.get_text(" ", strip=True)
    # Collapse consecutive spaces
    clean_text = " ".join(clean_text.split())

    return {
        "url": page_url,
        "title": title,
        "meta_description": meta_desc,
        "headings": headings,
        "paragraphs": paragraphs,
        "links": raw_links,
        "text": clean_text,
        "word_count": len(clean_text.split()),
    }
