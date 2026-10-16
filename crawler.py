"""
Crawler module.
Coordinates page fetching, HTML parsing, internal link discovery, site structure preview,
and LLM structured extraction with authentication support.
"""

from collections import deque
import logging
import time
from typing import Any
import requests

from fetcher import fetch_page
from html_parser import parse_html
from url_manager import (
    normalize_url,
    is_allowed_url,
    get_internal_links,
    get_internal_pages_metadata,
    classify_url_section,
)
from llm_extractor import extract_structured_data, synthesize_website_summary
from storage import save_to_json

logger = logging.getLogger(__name__)


def process_single_page(
    url: str,
    session: requests.Session | None = None,
    extract_with_llm: bool = True,
) -> dict[str, Any]:
    """
    Fetch, parse, and optionally extract structured LLM intelligence from a single URL.
    Uses the provided requests.Session to preserve authentication credentials and cookies.
    """
    normalized = normalize_url(url)
    if not normalized:
        raise ValueError(f"Invalid URL provided: {url}")

    print(f"\n[+] Fetching URL: {normalized}")
    response = fetch_page(normalized, session=session)

    content_type = response.get("content_type", "").lower()
    if "text/html" not in content_type and "application/xhtml+xml" not in content_type:
        raise ValueError(
            f"Expected HTML response, but received Content-Type: '{content_type}'"
        )

    final_url = response.get("final_url", normalized)
    print(f"    Status: {response['status_code']} | Parsing HTML content...")
    extracted = parse_html(response["html"], page_url=final_url)
    extracted["status_code"] = response["status_code"]
    extracted["requested_url"] = normalized
    extracted["final_url"] = final_url
    extracted["cookies_active"] = bool(response.get("cookies"))

    if extract_with_llm:
        print(f"    Extracting structured intelligence with Mistral LLM...")
        try:
            llm_data = extract_structured_data(
                page_title=extracted["title"],
                page_text=extracted["text"],
                page_url=final_url,
            )
            extracted["llm_analysis"] = llm_data
            print(f"    LLM Extraction complete! (Model: {llm_data.get('model_used')})")
        except Exception as error:
            print(f"    [!] LLM extraction warning: {error}")
            extracted["llm_analysis"] = {
                "error": str(error),
                "summary": "LLM extraction could not be completed.",
                "topics": [],
                "key_facts": [],
                "entities": [],
                "contact_information": [],
            }
    else:
        extracted["llm_analysis"] = None

    return extracted


def discover_site_structure(
    start_url: str,
    session: requests.Session | None = None,
) -> dict[str, Any]:
    """
    Perform a fast discovery scan of the target website:
    1. Fetches the starting URL (reusing authenticated session if available).
    2. Discovers all internal links and categorizes them into sections.
    3. Returns the total count, grouped sections, and indexed list of discovered pages.
    """
    normalized = normalize_url(start_url)
    if not normalized:
        raise ValueError(f"Invalid URL: {start_url}")

    print(f"\n[*] Scanning site structure and discovering sections for: {normalized} ...")
    response = fetch_page(normalized, session=session)
    final_url = normalize_url(response.get("final_url", normalized)) or normalized

    extracted = parse_html(response["html"], page_url=final_url)
    extracted["status_code"] = response["status_code"]
    extracted["requested_url"] = normalized
    extracted["final_url"] = final_url

    # Collect metadata for all internal links
    discovered_meta = get_internal_pages_metadata(
        extracted["links"],
        current_url=final_url,
        start_url=normalized,
    )

    # Put the start page at index 1
    start_section = classify_url_section(final_url, normalized)
    all_pages = [{
        "index": 1,
        "url": final_url,
        "title": extracted.get("title") or "Home / Starting Page",
        "section": start_section,
    }]

    seen_urls = {final_url}

    for item in discovered_meta:
        if item["url"] not in seen_urls:
            seen_urls.add(item["url"])
            all_pages.append({
                "index": len(all_pages) + 1,
                "url": item["url"],
                "title": item["title"],
                "section": item["section"],
            })

    # Group into sections
    sections: dict[str, list[dict[str, Any]]] = {}
    for p in all_pages:
        sec = p["section"]
        sections.setdefault(sec, []).append(p)

    return {
        "start_url": normalized,
        "final_url": final_url,
        "total_pages": len(all_pages),
        "sections": sections,
        "all_pages": all_pages,
        "start_page_data": extracted,
    }


def crawl_website(
    start_url: str,
    session: requests.Session | None = None,
    target_urls: list[str] | None = None,
    max_pages: int = 10,
    extract_with_llm: bool = True,
    delay_seconds: float = 1.0,
    initial_page_data: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    """
    Crawl a website starting from start_url or a specific list of target URLs.
    Supports authenticated requests through session and extracts structured LLM intelligence.

    Returns:
        (pages, site_summary)
    """
    start_url = normalize_url(start_url)
    if not start_url:
        raise ValueError("Please provide a valid HTTP(S) URL.")

    pages: list[dict[str, Any]] = []

    # If specific target URLs were selected by the user (from section or page list)
    if target_urls:
        url_list = [u for u in target_urls if u]
        total_targets = min(len(url_list), max_pages) if max_pages else len(url_list)
        queue = deque(url_list[:total_targets])
        scheduled = set(queue)
    else:
        queue = deque([start_url])
        scheduled = {start_url}

    print(f"\n==================================================")
    print(f"  Starting crawl for: {start_url}")
    print(f"  Pages queued: {len(queue)} | LLM Enabled: {extract_with_llm}")
    if session and session.cookies:
        print(f"  Active Session Cookies: {len(session.cookies)}")
    print(f"==================================================")

    while queue and len(pages) < max_pages:
        current_url = queue.popleft()
        page_num = len(pages) + 1
        print(f"\n[{page_num}/{max_pages}] Fetching: {current_url}")

        try:
            # Optimize: Reuse pre-fetched start page if available
            if (
                initial_page_data
                and (current_url == initial_page_data.get("requested_url")
                     or current_url == initial_page_data.get("final_url"))
            ):
                extracted = initial_page_data
                final_url = extracted.get("final_url", current_url)
            else:
                response = fetch_page(current_url, session=session)
                content_type = response["content_type"].lower()

                if "text/html" not in content_type and "application/xhtml+xml" not in content_type:
                    print(f"  [-] Skipped: Non-HTML response ({content_type})")
                    continue

                final_url = normalize_url(response["final_url"])
                if not final_url:
                    print("  [-] Skipped: Invalid final URL after redirects.")
                    continue

                if not is_allowed_url(final_url, start_url):
                    print(f"  [-] Skipped: Redirected outside host ({final_url})")
                    continue

                extracted = parse_html(response["html"], page_url=final_url)
                extracted["status_code"] = response["status_code"]
                extracted["requested_url"] = current_url
                extracted["final_url"] = final_url

            # Extract structured intelligence via LLM
            if extract_with_llm:
                print(f"  [*] Processing through Mistral LLM...")
                try:
                    llm_data = extract_structured_data(
                        page_title=extracted["title"],
                        page_text=extracted["text"],
                        page_url=final_url,
                    )
                    extracted["llm_analysis"] = llm_data
                    print(f"  [+] Title: {extracted['title'][:60]}")
                    print(f"      Summary: {llm_data.get('summary', '')[:100]}...")
                except Exception as llm_err:
                    print(f"  [!] LLM warning: {llm_err}")
                    extracted["llm_analysis"] = {
                        "error": str(llm_err),
                        "summary": "LLM extraction failed.",
                        "topics": [],
                        "key_facts": [],
                        "entities": [],
                        "contact_information": [],
                    }
            else:
                extracted["llm_analysis"] = None

            pages.append(extracted)

            # If dynamic crawling (not restricted to a static user list), discover more links
            if not target_urls:
                new_links = get_internal_links(
                    extracted["links"],
                    current_url=final_url,
                    start_url=start_url,
                )

                discovered_count = 0
                for link in new_links:
                    if link not in scheduled and len(scheduled) < max_pages * 5:
                        scheduled.add(link)
                        queue.append(link)
                        discovered_count += 1

                if discovered_count > 0:
                    print(f"  [+] Discovered {discovered_count} new internal links (Queue: {len(queue)})")

        except Exception as error:
            print(f"  [!] Failed fetching {current_url}: {error}")

        # Politeness delay between page requests
        if queue and len(pages) < max_pages:
            time.sleep(delay_seconds)

    # Synthesize site-level intelligence if multiple pages were crawled
    site_summary = None
    if extract_with_llm and len(pages) > 1:
        print("\n[*] Synthesizing overall website summary with LLM...")
        try:
            site_summary = synthesize_website_summary(pages)
            print("  [+] Website synthesis complete!")
        except Exception as syn_err:
            print(f"  [!] Could not synthesize website summary: {syn_err}")

    return pages, site_summary


def save_pages_json(pages: list[dict[str, Any]], filename: str = "crawled_pages.json") -> None:
    """Save raw crawled pages list to a single JSON file."""
    save_to_json(pages, filename)
    print(f"\nSaved {len(pages)} pages to {filename}")
