# AI Website Intelligence & LLM Extractor

An automated system that fetches any entered website or webpage URL, parses and extracts the clean content, uses Mistral AI to extract structured facts, summaries, topics, and contact intelligence, and stores everything into an **executable Python script (`.py`)**, **JSON (`.json`)**, and a **Markdown report (`.md`)**.

---

## Features

- **Single URL or Multi-Page Crawl**:
  - **Single Page Mode**: Directly fetch and analyze any specific URL (blogs, homepages, product pages).
  - **Website Crawl Mode**: Crawl across internal links on the same domain up to any custom limit (`--max-pages`).
- **Resilient Web Fetcher & HTML Parser**:
  - Uses realistic browser headers and session handling to prevent `403 Forbidden` errors.
  - Automatically filters out binary assets (`.pdf`, `.png`, `.jpg`, `.zip`, `.mp4`).
  - Cleans scripts, styles, iframes, and extract title, meta descriptions, headings, paragraphs, and links.
- **Mistral LLM Intelligence Engine**:
  - Automatically handles `mistralai>=3.0` import compatibility.
  - Uses `ministral-8b-latest` (fast, free-tier friendly) with automatic fallback to `ministral-3b-latest` and `mistral-small-latest`.
  - Built-in exponential backoff retry for HTTP 429 rate limit errors.
  - Extracts executive summaries, topics, key facts, entities, and contact details.
  - Automatically generates an overarching site synthesis report when crawling multiple pages.
- **Multi-Format Storage**:
  - **Python Script (`.py`)**: Stores the data as an executable Python script with helper functions (`get_page_by_url`, `search_by_topic`, `get_all_key_facts`, `get_all_contacts`).
  - **JSON (`.json`)**: Formatted data dump for interoperability.
  - **Markdown (`.md`)**: Human-readable executive summary and detailed page breakdown.

---

## How to Run

### 1. Interactive Mode
Run the script without arguments and follow the prompts:
```bash
python main.py
```

### 2. Single Page Extraction
Fetch and extract intelligence from a single webpage:
```bash
python main.py --url https://example.com
```

### 3. Crawl Website (Multi-Page)
Crawl internal links on the website (e.g. up to 5 pages):
```bash
python main.py --url https://books.toscrape.com --crawl --max-pages 5
```

### 4. Fast Crawl Without LLM
Fetch and parse HTML without consuming LLM tokens:
```bash
python main.py --url https://example.com --no-llm
```

---

## Using the Generated Python Script

The system saves all extracted data into a `.py` file inside the `output/` folder (e.g. `output/example_com_intelligence.py`).

You can execute it directly:
```bash
python output/example_com_intelligence.py
```

Or import it into your own Python projects:
```python
import sys
sys.path.append("output")

from example_com_intelligence import (
    EXTRACTED_PAGES,
    get_all_key_facts,
    search_by_topic,
    get_all_contacts,
)

# Search pages matching a topic keyword
results = search_by_topic("pricing")

# Get all key facts extracted across all pages
facts = get_all_key_facts()
for fact in facts:
    print("-", fact)
```

---

## Project Structure

```
website-tracker/
├── crawler.py           # Crawling queue, BFS link manager, site synthesis coordinator
├── fetcher.py           # HTTP requests with browser headers and encoding detection
├── html_parser.py       # BeautifulSoup extraction of clean text, headings, and links
├── llm_extractor.py     # Mistral AI client with retry, fallback models, and schema extraction
├── main.py              # CLI and interactive user interface
├── storage.py           # Multi-format exporter (Python script, JSON, Markdown)
├── test_llm.py          # Verification test for Mistral LLM extraction
├── test_urls.py         # Verification test for URL normalization and filters
├── output/              # Auto-generated .py, .json, and .md output files
├── .env                 # Environment variables (MISTRAL_API_KEY, MISTRAL_MODEL)
└── requirements.txt     # Python dependencies
```

