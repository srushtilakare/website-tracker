"""
Main CLI Application for Website Intelligence and LLM Extractor.
Fetches single URLs or crawls full websites, analyzes them with Mistral LLM,
and stores everything in Python scripts (.py), JSON (.json), and Markdown reports (.md).
"""

import argparse
import sys
from pathlib import Path
from urllib.parse import urlsplit

# Ensure UTF-8 console output on Windows to prevent UnicodeEncodeError
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

from crawler import crawl_website, process_single_page
from storage import save_all_formats


def get_safe_slug(url: str) -> str:
    """Generate a clean filesystem slug from a URL hostname."""
    try:
        hostname = urlsplit(url).hostname or "site"
        slug = hostname.replace("www.", "").replace(".", "_")
        return slug or "site"
    except Exception:
        return "site"


def run_pipeline(
    url: str,
    crawl_mode: bool = False,
    max_pages: int = 5,
    enable_llm: bool = True,
    output_dir: str = "output",
) -> None:
    """Execute the fetch, LLM extraction, and multi-format storage pipeline."""
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    slug = get_safe_slug(url)

    if not crawl_mode:
        # Single page mode
        print(f"\n========================================================")
        print(f"  MODE: Single Webpage Intelligence Extraction")
        print(f"  TARGET: {url}")
        print(f"  LLM EXTRACTION: {'Enabled' if enable_llm else 'Disabled'}")
        print(f"========================================================")

        page_record = process_single_page(url, extract_with_llm=enable_llm)
        pages = [page_record]
        site_summary = None

    else:
        # Multi-page crawl mode
        pages, site_summary = crawl_website(
            start_url=url,
            max_pages=max_pages,
            extract_with_llm=enable_llm,
        )

    if not pages:
        print("\n[!] No pages could be successfully extracted.")
        return

    # Save to all formats (Python script, JSON, and Markdown)
    base_name = f"{slug}_intelligence"
    saved_files = save_all_formats(
        pages=pages,
        site_summary=site_summary,
        output_dir=output_dir,
        base_name=base_name,
    )

    print("\n" + "=" * 60)
    print("                    EXTRACTION COMPLETE")
    print("=" * 60)
    print(f"  Total Pages Processed : {len(pages)}")
    print(f"  Outputs Saved To      : {Path(output_dir).resolve()}")
    print(f"    * Python Script     : {saved_files['python'].name} (can be imported or run directly)")
    print(f"    * JSON Data         : {saved_files['json'].name}")
    print(f"    * Markdown Report   : {saved_files['markdown'].name}")
    print("-" * 60)

    # Print a quick preview of the extracted data
    for i, p in enumerate(pages, start=1):
        llm = p.get("llm_analysis") or {}
        title = p.get("title") or llm.get("page_title") or "Untitled"
        print(f"\n[{i}] {title}")
        print(f"    URL: {p.get('final_url', p.get('url'))}")
        if llm.get("summary"):
            print(f"    Summary: {llm['summary']}")
        if llm.get("topics"):
            print(f"    Topics: {', '.join(llm['topics'])}")
        if llm.get("contact_information"):
            print(f"    Contacts: {', '.join(llm['contact_information'])}")

    print("\n[SUCCESS] All data has been stored successfully.")


def interactive_menu() -> None:
    """Prompt the user interactively when no CLI arguments are supplied."""
    print("=" * 60)
    print("   AI Website Fetcher & Intelligence Extractor")
    print("=" * 60)

    url = input("Enter website URL (e.g. https://example.com): ").strip()
    while not url:
        print("URL cannot be empty.")
        url = input("Enter website URL: ").strip()

    print("\nSelect Mode:")
    print("  [1] Single Page (Fetch only this entered URL) [Default]")
    print("  [2] Crawl Website (Discover internal links and extract multiple pages)")
    mode_choice = input("Enter 1 or 2 [Default: 1]: ").strip()

    is_crawl = mode_choice == "2"
    max_pages = 5
    if is_crawl:
        pages_input = input("Enter maximum pages to crawl [Default: 5]: ").strip()
        if pages_input.isdigit() and int(pages_input) > 0:
            max_pages = int(pages_input)

    llm_choice = input("Enable Mistral LLM analysis? (y/n) [Default: y]: ").strip().lower()
    enable_llm = llm_choice != "n"

    run_pipeline(
        url=url,
        crawl_mode=is_crawl,
        max_pages=max_pages,
        enable_llm=enable_llm,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch, crawl, and extract structured intelligence from websites using Mistral LLM."
    )
    parser.add_argument("--url", "-u", type=str, help="Target website or webpage URL.")
    parser.add_argument("--crawl", "-c", action="store_true", help="Crawl internal links across the website.")
    parser.add_argument("--max-pages", "-m", type=int, default=5, help="Maximum pages to crawl (default: 5).")
    parser.add_argument("--no-llm", action="store_true", help="Skip LLM extraction and only fetch/parse HTML.")
    parser.add_argument("--output-dir", "-o", type=str, default="output", help="Directory to save output files.")

    args = parser.parse_args()

    if args.url:
        run_pipeline(
            url=args.url,
            crawl_mode=args.crawl,
            max_pages=args.max_pages,
            enable_llm=not args.no_llm,
            output_dir=args.output_dir,
        )
    else:
        interactive_menu()


if __name__ == "__main__":
    main()
