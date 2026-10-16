"""
URL normalization and filtering module.
Resolves relative URLs, enforces same-domain crawling rules, and filters out non-HTML assets.
"""

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
