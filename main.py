"""
Main CLI & Interactive Application for Website Intelligence & LLM Extractor.
Features:
- Authenticated Web Scraping (Cookie, Bearer token, Basic auth, Form login)
- Site Structure Discovery & Section Preview (shows sections and total pages before crawling)
- Targeted Selection (crawl all, first N pages, specific sections, or specific page numbers)
- Mistral AI Structured Fact Extraction
- Multi-format Persistence (.py Python script, .json, .md Markdown report)
"""

import argparse
import re
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

import requests
from auth_manager import create_authenticated_session
from crawler import crawl_website, process_single_page, discover_site_structure
from storage import save_all_formats


def get_safe_slug(url: str) -> str:
    """Generate a clean filesystem slug from a URL hostname."""
    try:
        hostname = urlsplit(url).hostname or "site"
        slug = hostname.replace("www.", "").replace(".", "_")
        return slug or "site"
    except Exception:
        return "site"


def parse_page_indices(input_str: str, max_limit: int) -> list[int]:
    """
    Parse a range/comma string into 1-based indices.
    Example: '1, 3, 5-8' -> [1, 3, 5, 6, 7, 8]
    """
    indices = set()
    parts = [p.strip() for p in input_str.split(",") if p.strip()]

    for part in parts:
        if "-" in part:
            bounds = part.split("-", 1)
            if bounds[0].strip().isdigit() and bounds[1].strip().isdigit():
                start = max(1, int(bounds[0]))
                end = min(max_limit, int(bounds[1]))
                if start <= end:
                    indices.update(range(start, end + 1))
        elif part.isdigit():
            val = int(part)
            if 1 <= val <= max_limit:
                indices.add(val)

    return sorted(indices)


def configure_interactive_auth() -> requests.Session | None:
    """Prompt the user for authentication credentials if required."""
    print("\n" + "-" * 50)
    print("  AUTHENTICATION CONFIGURATION")
    print("-" * 50)
    print("Does this website require authentication or login?")
    auth_choice = input("Enter 'y' for Yes or 'n' for No [Default: n]: ").strip().lower()

    if auth_choice != "y":
        return None

    print("\nSelect Authentication Method:")
    print("  [1] Cookie String (Paste session cookie from your browser dev tools)")
    print("  [2] Cookie File (JSON or text file path with cookies)")
    print("  [3] Form Login (Login URL + Username/Email + Password)")
    print("  [4] Bearer Token (JWT / API Token)")
    print("  [5] HTTP Basic Auth (Username + Password)")

    method = input("Enter option [1-5]: ").strip()

    try:
        if method == "1":
            cookie_str = input("Paste your Cookie string (e.g. sessionid=abc; token=xyz): ").strip()
            return create_authenticated_session(auth_type="cookie", cookie_str=cookie_str)

        elif method == "2":
            file_path = input("Enter cookie file path: ").strip()
            return create_authenticated_session(auth_type="cookie", cookie_file=file_path)

        elif method == "3":
            login_url = input("Enter Login URL (e.g. https://example.com/login): ").strip()
            username = input("Enter Username / Email: ").strip()
            password = input("Enter Password: ").strip()
            return create_authenticated_session(
                auth_type="login_form",
                login_url=login_url,
                username=username,
                password=password,
            )

        elif method == "4":
            token = input("Enter Bearer Token: ").strip()
            return create_authenticated_session(auth_type="bearer", bearer_token=token)

        elif method == "5":
            user = input("Enter Username: ").strip()
            pwd = input("Enter Password: ").strip()
            return create_authenticated_session(auth_type="basic", basic_auth=(user, pwd))

        else:
            print("[!] Invalid option. Continuing without authentication.")
            return None

    except Exception as auth_err:
        print(f"[!] Authentication setup failed: {auth_err}")
        cont = input("Continue without authentication? (y/n) [Default: y]: ").strip().lower()
        if cont == "n":
            sys.exit(1)
        return None


def display_site_discovery(discovery: dict) -> None:
    """Display the discovered sections, total counts, and sample pages."""
    total = discovery["total_pages"]
    sections = discovery["sections"]
    all_pages = discovery["all_pages"]

    print("\n" + "=" * 65)
    print("                  SITE DISCOVERY & STRUCTURE")
    print("=" * 65)
    print(f"Target URL: {discovery['start_url']}")
    print(f"Total Discovered Pages on Domain: {total}")
    print(f"Discovered Sections / Categories: {len(sections)}")
    print("-" * 65)

    # Print sections summary
    sorted_sections = sorted(sections.items(), key=lambda x: -len(x[1]))
    for idx, (sec_name, pages) in enumerate(sorted_sections, start=1):
        sample_title = pages[0]["title"][:35]
        print(f"  [{idx}] {sec_name:<25} ({len(pages)} pages) -> e.g. \"{sample_title}\"")

    # Print sample pages preview
    print("\nSample Pages Discovered:")
    preview_limit = min(8, total)
    for p in all_pages[:preview_limit]:
        title_snippet = p["title"][:45]
        print(f"   {p['index']:>2}. {title_snippet} ({p['url']})")

    if total > preview_limit:
        print(f"   ... and {total - preview_limit} more pages discovered.")
    print("=" * 65)


def run_pipeline(
    url: str,
    session: requests.Session | None = None,
    target_urls: list[str] | None = None,
    max_pages: int = 5,
    enable_llm: bool = True,
    output_dir: str = "output",
    initial_page_data: dict | None = None,
) -> None:
    """Execute the crawl, LLM extraction, and multi-format storage pipeline."""
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    slug = get_safe_slug(url)

    pages, site_summary = crawl_website(
        start_url=url,
        session=session,
        target_urls=target_urls,
        max_pages=max_pages,
        extract_with_llm=enable_llm,
        initial_page_data=initial_page_data,
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

    print("\n" + "=" * 65)
    print("                    EXTRACTION COMPLETE")
    print("=" * 65)
    print(f"  Total Pages Processed : {len(pages)}")
    print(f"  Outputs Saved To      : {Path(output_dir).resolve()}")
    print(f"    * Python Script     : {saved_files['python'].name} (executable & importable)")
    print(f"    * JSON Data         : {saved_files['json'].name}")
    print(f"    * Markdown Report   : {saved_files['markdown'].name}")
    print("-" * 65)

    # Print a quick preview of extracted data
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
    """Guided interactive wizard for site discovery, auth, and extraction."""
    print("=" * 65)
    print("     AI Website Intelligence Extractor & Crawler")
    print("=" * 65)

    url = input("Enter website URL (e.g. https://example.com): ").strip()
    while not url:
        print("URL cannot be empty.")
        url = input("Enter website URL: ").strip()

    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    # 1. Authentication configuration
    session = configure_interactive_auth()

    # 2. Site Discovery & Structure Preview
    try:
        discovery = discover_site_structure(url, session=session)
        display_site_discovery(discovery)
    except Exception as disc_err:
        print(f"\n[!] Site discovery encountered an issue: {disc_err}")
        print("    Proceeding with single page mode.")
        discovery = None

    target_urls = None
    max_pages = 5

    if discovery and discovery["total_pages"] > 1:
        total = discovery["total_pages"]
        sections = discovery["sections"]
        all_pages = discovery["all_pages"]
        sorted_sections = sorted(sections.items(), key=lambda x: -len(x[1]))

        print("\nHow would you like to crawl?")
        print(f"  [A] Crawl ALL {total} discovered pages")
        print(f"  [N] Crawl the top N pages (e.g. enter 5 or 10)")
        print(f"  [S] Crawl specific section(s) (e.g. choose by section number)")
        print(f"  [P] Crawl specific page number(s) (e.g. enter 1, 3, 5-8)")
        print(f"  [1] Crawl ONLY the single starting page")

        user_input = input("\nEnter choice [A / N / S / P / 1, or enter page count]: ").strip()

        # Handle direct number input (e.g. user just typed "10")
        if user_input.isdigit():
            count = int(user_input)
            max_pages = min(count, total)
            target_urls = [p["url"] for p in all_pages[:max_pages]]

        elif user_input.lower() in {"a", "all"}:
            max_pages = total
            target_urls = [p["url"] for p in all_pages]

        elif user_input.lower() in {"n", "number"}:
            num_str = input(f"Enter number of pages to crawl (1 to {total}) [Default: 5]: ").strip()
            max_pages = int(num_str) if num_str.isdigit() and int(num_str) > 0 else 5
            max_pages = min(max_pages, total)
            target_urls = [p["url"] for p in all_pages[:max_pages]]

        elif user_input.lower() in {"s", "section", "sections"}:
            sec_choice = input(f"Enter section numbers separated by commas (1 to {len(sorted_sections)}): ").strip()
            chosen_sec_indices = parse_page_indices(sec_choice, len(sorted_sections))
            if chosen_sec_indices:
                chosen_urls = []
                for sec_idx in chosen_sec_indices:
                    sec_name, sec_pages = sorted_sections[sec_idx - 1]
                    print(f"  -> Added {len(sec_pages)} pages from section '{sec_name}'")
                    chosen_urls.extend([p["url"] for p in sec_pages])
                target_urls = list(dict.fromkeys(chosen_urls))  # deduplicate
                max_pages = len(target_urls)
            else:
                print("  [!] Invalid selection. Falling back to top 5 pages.")
                max_pages = min(5, total)
                target_urls = [p["url"] for p in all_pages[:max_pages]]

        elif user_input.lower() in {"p", "page", "pages"}:
            page_choice = input(f"Enter page numbers to crawl (e.g. 1, 3, 5-8, max {total}): ").strip()
            chosen_page_indices = parse_page_indices(page_choice, total)
            if chosen_page_indices:
                target_urls = [all_pages[idx - 1]["url"] for idx in chosen_page_indices]
                max_pages = len(target_urls)
                print(f"  -> Selected {len(target_urls)} specific pages.")
            else:
                print("  [!] Invalid page numbers. Falling back to start page.")
                target_urls = [all_pages[0]["url"]]
                max_pages = 1

        elif user_input == "1":
            target_urls = [discovery["final_url"]]
            max_pages = 1

        else:
            # Default fallback
            max_pages = min(5, total)
            target_urls = [p["url"] for p in all_pages[:max_pages]]

    else:
        # Single page fallback if only 1 page was found
        target_urls = [url]
        max_pages = 1

    llm_choice = input("\nEnable Mistral LLM analysis? (y/n) [Default: y]: ").strip().lower()
    enable_llm = llm_choice != "n"

    initial_page_data = discovery.get("start_page_data") if discovery else None

    run_pipeline(
        url=url,
        session=session,
        target_urls=target_urls,
        max_pages=max_pages,
        enable_llm=enable_llm,
        initial_page_data=initial_page_data,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch, crawl, and extract structured intelligence from websites using Mistral LLM with authentication and section selection."
    )
    # Target and mode
    parser.add_argument("--url", "-u", type=str, help="Target website or webpage URL.")
    parser.add_argument("--crawl", "-c", action="store_true", help="Crawl internal links across the website.")
    parser.add_argument("--max-pages", "-m", type=int, default=5, help="Maximum pages to crawl (default: 5).")
    parser.add_argument("--pages", type=str, help="Specific page indices to crawl from discovery (e.g. '1,3,5-8').")
    parser.add_argument("--preview-only", action="store_true", help="Perform discovery scan and print sections without crawling.")
    parser.add_argument("--no-llm", action="store_true", help="Skip LLM extraction and only fetch/parse HTML.")
    parser.add_argument("--output-dir", "-o", type=str, default="output", help="Directory to save output files.")

    # Authentication options
    parser.add_argument("--cookie", type=str, help="Cookie string for authentication (e.g. 'sessionid=abc; token=xyz').")
    parser.add_argument("--cookie-file", type=str, help="File path containing cookies (JSON or text).")
    parser.add_argument("--bearer", type=str, help="Bearer token for Authorization header.")
    parser.add_argument("--basic-auth", type=str, help="HTTP Basic auth in format 'username:password'.")
    parser.add_argument("--login-url", type=str, help="URL to perform form login.")
    parser.add_argument("--username", type=str, help="Username or email for form login.")
    parser.add_argument("--password", type=str, help="Password for form login.")

    args = parser.parse_args()

    # CLI mode
    if args.url:
        # Build session if auth flags provided
        session = None
        basic_tuple = tuple(args.basic_auth.split(":", 1)) if args.basic_auth and ":" in args.basic_auth else None

        if (
            args.cookie
            or args.cookie_file
            or args.bearer
            or basic_tuple
            or (args.login_url and args.username and args.password)
        ):
            session = create_authenticated_session(
                cookie_str=args.cookie,
                cookie_file=args.cookie_file,
                bearer_token=args.bearer,
                basic_auth=basic_tuple,
                login_url=args.login_url,
                username=args.username,
                password=args.password,
            )

        if args.preview_only:
            discovery = discover_site_structure(args.url, session=session)
            display_site_discovery(discovery)
            return

        target_urls = None
        max_pages = args.max_pages
        initial_data = None

        if args.crawl or args.pages:
            discovery = discover_site_structure(args.url, session=session)
            initial_data = discovery.get("start_page_data")
            all_pages = discovery["all_pages"]

            if args.pages:
                indices = parse_page_indices(args.pages, discovery["total_pages"])
                target_urls = [all_pages[idx - 1]["url"] for idx in indices]
                max_pages = len(target_urls)
            else:
                max_pages = min(args.max_pages, discovery["total_pages"])
                target_urls = [p["url"] for p in all_pages[:max_pages]]
        else:
            # Single page
            max_pages = 1

        run_pipeline(
            url=args.url,
            session=session,
            target_urls=target_urls,
            max_pages=max_pages,
            enable_llm=not args.no_llm,
            output_dir=args.output_dir,
            initial_page_data=initial_data,
        )

    else:
        # Interactive mode
        interactive_menu()


if __name__ == "__main__":
    main()
