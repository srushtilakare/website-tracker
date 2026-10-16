"""
Webpage fetcher module.
Fetches web pages using requests with browser headers, timeouts, and error handling.
"""

import logging
from typing import Any
import requests

logger = logging.getLogger(__name__)

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive",
}


def fetch_page(url: str, timeout: int = 15, headers: dict[str, str] | None = None) -> dict[str, Any]:
    """
    Fetch a webpage and return its URL, status code, content type, and HTML text.
    
    Raises:
        requests.RequestException on network or HTTP errors.
    """
    req_headers = {**DEFAULT_HEADERS, **(headers or {})}

    session = requests.Session()
    response = session.get(
        url,
        headers=req_headers,
        timeout=timeout,
        allow_redirects=True,
    )

    # Detect encoding if not set properly
    if response.encoding is None or response.encoding == "ISO-8859-1":
        response.encoding = response.apparent_encoding or "utf-8"

    response.raise_for_status()

    return {
        "requested_url": url,
        "final_url": response.url,
        "status_code": response.status_code,
        "content_type": response.headers.get("Content-Type", ""),
        "html": response.text,
    }
