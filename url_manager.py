"""
URL normalization, filtering, and section classification module.
Resolves relative URLs, enforces same-domain crawling rules, filters out non-HTML assets,
and categorizes URLs into logical website sections.
"""

import re
from urllib.parse import urljoin, urlsplit, urlunsplit

IGNORED_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".ico",
    ".pdf", ".zip", ".tar", ".gz", ".rar", ".7z",
    ".mp3", ".mp4", ".avi", ".mov", ".mkv",
    ".css", ".js", ".json", ".xml",
    ".woff", ".woff2", ".ttf", ".eot",
}


def normalize_url(url: str, base_url: str | None = None) -> str | None:
    """
    Convert a URL into a consistent absolute URL.
    Return None for invalid or unsupported URLs.
    """
    if not url or not url.strip():
        return None

    url = url.strip()

    # Resolve relative URLs against the current page.
    if base_url:
        url = urljoin(base_url, url)

    try:
        parsed = urlsplit(url)

        if parsed.scheme.lower() not in {"http", "https"}:
            return None

        if not parsed.hostname:
            return None

        # Reject URLs containing embedded credentials.
        if parsed.username is not None or parsed.password is not None:
            return None

        scheme = parsed.scheme.lower()
        hostname = parsed.hostname.lower()

        # Preserve non-default ports.
        port = parsed.port

        if port is not None:
            if not (
                (scheme == "http" and port == 80)
                or (scheme == "https" and port == 443)
            ):
                netloc = f"{hostname}:{port}"
            else:
                netloc = hostname
        else:
            netloc = hostname

        # Normalize an empty path to "/".
        path = parsed.path or "/"

        # Fragments are not sent to the web server.
        # Query parameters are preserved.
        return urlunsplit((
            scheme,
            netloc,
            path,
            parsed.query,
            "",
        ))

    except ValueError:
        return None


def is_allowed_url(url: str, start_url: str) -> bool:
    """
    Allow only URLs on the same hostname as the starting URL.
    Also reject common binary/asset file extensions.
    """
    normalized = normalize_url(url)
    start = normalize_url(start_url)

    if not normalized or not start:
        return False

    candidate_split = urlsplit(normalized)
    start_split = urlsplit(start)

    # Check hostname match
    if candidate_split.hostname != start_split.hostname:
        return False

    # Check ignored extensions
    path_lower = candidate_split.path.lower()
    for ext in IGNORED_EXTENSIONS:
        if path_lower.endswith(ext):
            return False

    return True


def classify_url_section(url: str, start_url: str | None = None) -> str:
    """
    Classify a URL into a logical website section based on path hierarchy.
    Examples:
      - https://example.com/ -> 'Home / Root'
      - https://example.com/about.html -> 'General Pages'
      - https://example.com/blog/ai-update -> '/blog/'
      - https://example.com/products/cameras/c1 -> '/products/'
      - https://example.com/docs/api/v1 -> '/docs/api/'
    """
    parsed = urlsplit(url)
    path = parsed.path.strip("/")

    if not path:
        return "Home / Root"

    segments = [s for s in path.split("/") if s]
    if not segments:
        return "Home / Root"

    first = segments[0].lower()

    # Check if first segment is a standalone page file (e.g. about.html, privacy.php)
    if any(first.endswith(ext) for ext in [".html", ".htm", ".php", ".asp", ".aspx"]):
        clean_name = first.split(".")[0].replace("-", " ").replace("_", " ").title()
        return "General Pages"

    # Multi-level categorization for deep structures like /docs/api/ or /category/books/
    if len(segments) > 1 and segments[1].lower() in {"api", "guide", "category", "v1", "v2", "topics"}:
        return f"/{first}/{segments[1].lower()}/"

    return f"/{first}/"


def clean_slug_to_title(url: str) -> str:
    """Derive a readable title from a URL path or query when anchor text is missing."""
    parsed = urlsplit(url)
    path = parsed.path.strip("/")
    if not path:
        return "Home"

    segments = [s for s in path.split("/") if s]
    last_seg = segments[-1]
    # Remove extension if any
    last_seg = re.sub(r"\.(html|htm|php|aspx|asp)$", "", last_seg, flags=re.IGNORECASE)
    # Remove trailing ID patterns like _1000 or -12345
    last_seg = re.sub(r"[_\-]\d+$", "", last_seg)
    # Replace dashes and underscores with spaces
    title = re.sub(r"[_\-]+", " ", last_seg).strip().title()
    return title or "Page"


def get_internal_links(
    links: list[dict],
    current_url: str,
    start_url: str,
) -> list[str]:
    """
    Resolve extracted links and return unique, allowed URLs.
    """
    internal_links = set()

    for link in links:
        href = link.get("href", "")

        absolute_url = normalize_url(
            href,
            base_url=current_url,
        )

        if absolute_url and is_allowed_url(
            absolute_url,
            start_url,
        ):
            internal_links.add(absolute_url)

    return sorted(internal_links)


def get_internal_pages_metadata(
    links: list[dict],
    current_url: str,
    start_url: str,
) -> list[dict]:
    """
    Resolve extracted links and return unique page items with:
    - url: normalized absolute URL
    - title: anchor text or inferred title
    - section: classified section category
    """
    seen_urls = set()
    pages = []

    for link in links:
        href = link.get("href", "")
        text = (link.get("text") or "").strip()

        absolute_url = normalize_url(href, base_url=current_url)

        if absolute_url and is_allowed_url(absolute_url, start_url):
            if absolute_url not in seen_urls:
                seen_urls.add(absolute_url)
                title = text if text and len(text) > 1 and not text.isdigit() else clean_slug_to_title(absolute_url)
                section = classify_url_section(absolute_url, start_url)
                pages.append({
                    "url": absolute_url,
                    "title": title,
                    "section": section,
                })

    return pages
