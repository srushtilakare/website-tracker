"""
Storage module.
Stores extracted website data and LLM intelligence into multiple formats:
- Python script (.py file with executable data structure and helper query functions)
- JSON file (.json file formatted with indentation)
- Markdown report (.md file with formatted executive tables and summaries)
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any
import pprint


def save_to_json(data: dict[str, Any] | list[Any], filepath: str | Path) -> Path:
    """Save data as pretty-printed UTF-8 JSON."""
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return path


def save_to_python_script(
    data: dict[str, Any] | list[Any],
    filepath: str | Path,
    var_name: str = "EXTRACTED_PAGES",
) -> Path:
    """
    Save the extracted data into a standalone, executable Python script (.py).
    Includes helper search functions so the data can be imported or queried directly.
    """
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().isoformat()
    formatted_data = pprint.pformat(data, indent=2, width=100, sort_dicts=False)

    script_content = f'''"""
Auto-generated Website Intelligence Data Script.
Generated on: {timestamp}
This script contains all extracted webpage content and LLM intelligence.
You can import this file into any Python project or run it directly.
"""

from typing import Any, List, Dict, Optional

# Timestamp of data extraction
GENERATED_AT = "{timestamp}"

# Full structured data extracted by the crawler and LLM
{var_name}: List[Dict[str, Any]] = {formatted_data}


def get_all_pages() -> List[Dict[str, Any]]:
    """Return all extracted page records."""
    return {var_name}


def get_page_by_url(url: str) -> Optional[Dict[str, Any]]:
    """Find a single page record by its exact URL."""
    for page in {var_name}:
        if page.get("url") == url or page.get("final_url") == url:
            return page
    return None


def search_by_topic(topic_keyword: str) -> List[Dict[str, Any]]:
    """Filter pages that contain the given topic keyword."""
    keyword_lower = topic_keyword.lower()
    matches = []
    for page in {var_name}:
        llm = page.get("llm_analysis", {{}})
        topics = [t.lower() for t in llm.get("topics", [])]
        if any(keyword_lower in t for t in topics):
            matches.append(page)
    return matches


def get_all_key_facts() -> List[str]:
    """Return a flat list of all key facts extracted across all pages."""
    all_facts = []
    for page in {var_name}:
        llm = page.get("llm_analysis", {{}})
        all_facts.extend(llm.get("key_facts", []))
    return all_facts


def get_all_contacts() -> List[str]:
    """Return a flat list of all contact info extracted across all pages."""
    all_contacts = []
    for page in {var_name}:
        llm = page.get("llm_analysis", {{}})
        all_contacts.extend(llm.get("contact_information", []))
    return list(dict.fromkeys(all_contacts))  # Deduplicate preserving order


if __name__ == "__main__":
    print("=" * 60)
    print(f"Website Intelligence Data - Generated: {{GENERATED_AT}}")
    print(f"Total Pages Stored: {{len({var_name})}}")
    print("=" * 60)

    for i, p in enumerate({var_name}, start=1):
        llm = p.get("llm_analysis", {{}})
        title = p.get("title") or llm.get("page_title") or "Untitled"
        url = p.get("url") or p.get("final_url", "No URL")
        print(f"\\n[{{i}}] {{title}}")
        print(f"    URL: {{url}}")
        if llm.get("summary"):
            print(f"    Summary: {{llm.get('summary')[:140]}}...")
        if llm.get("topics"):
            print(f"    Topics: {{', '.join(llm.get('topics', []))}}")

    contacts = get_all_contacts()
    if contacts:
        print("\\nContact Details Discovered:")
        for c in contacts:
            print(f"  * {{c}}")
'''

    with open(path, "w", encoding="utf-8") as f:
        f.write(script_content)

    return path


def save_to_markdown_report(
    pages: list[dict[str, Any]],
    site_summary: dict[str, Any] | None,
    filepath: str | Path,
) -> Path:
    """Generate a clean, readable Markdown report of the website crawl and LLM extraction."""
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lines = [
        f"# Website Intelligence Report",
        f"*Generated on: {timestamp}*",
        f"*Total Pages Extracted: {len(pages)}*",
        "",
    ]

    # Site-level summary section if available
    if site_summary and isinstance(site_summary, dict) and not site_summary.get("error"):
        name = site_summary.get("website_name", "Target Website")
        overview = site_summary.get("executive_overview", "")
        lines.extend([
            f"## Executive Overview: {name}",
            f"{overview}",
            "",
        ])

        categories = site_summary.get("primary_categories", [])
        if categories:
            lines.append("### Primary Categories / Offerings")
            for cat in categories:
                lines.append(f"- {cat}")
            lines.append("")

        highlights = site_summary.get("key_highlights", [])
        if highlights:
            lines.append("### Key Highlights")
            for h in highlights:
                lines.append(f"- {h}")
            lines.append("")

    # Page breakdown
    lines.append("## Detailed Page Breakdown")
    lines.append("")

    for i, page in enumerate(pages, start=1):
        llm = page.get("llm_analysis", {})
        title = page.get("title") or llm.get("page_title") or f"Page {i}"
        url = page.get("url") or page.get("final_url", "N/A")
        summary = llm.get("summary") or "No LLM summary available."
        topics = llm.get("topics", [])
        facts = llm.get("key_facts", [])
        entities = llm.get("entities", [])
        contacts = llm.get("contact_information", [])

        lines.extend([
            f"### {i}. {title}",
            f"**URL:** [{url}]({url})  ",
            f"**Word Count:** {page.get('word_count', 0)}  ",
            f"**Summary:** {summary}",
            "",
        ])

        if topics:
            lines.append(f"**Topics:** `{', '.join(topics)}`  ")

        if facts:
            lines.append("**Key Facts:**")
            for fact in facts:
                lines.append(f"- {fact}")
            lines.append("")

        if entities:
            lines.append(f"**Notable Entities:** {', '.join(entities)}  ")

        if contacts:
            lines.append("**Contacts Discovered:**")
            for c in contacts:
                lines.append(f"- {c}")
            lines.append("")

        lines.append("---")
        lines.append("")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return path


def save_all_formats(
    pages: list[dict[str, Any]],
    site_summary: dict[str, Any] | None = None,
    output_dir: str | Path = "output",
    base_name: str = "extracted_data",
) -> dict[str, Path]:
    """Save extracted pages in JSON, Python script (.py), and Markdown report (.md) formats."""
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    json_path = out_path / f"{base_name}.json"
    py_path = out_path / f"{base_name}.py"
    md_path = out_path / f"{base_name}_report.md"

    save_to_json(
        {"pages": pages, "site_summary": site_summary},
        json_path,
    )
    save_to_python_script(pages, py_path)
    save_to_markdown_report(pages, site_summary, md_path)

    return {
        "json": json_path,
        "python": py_path,
        "markdown": md_path,
    }

