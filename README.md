# AI Website Intelligence & LLM Extractor

An automated system that fetches any website or webpage URL (including **authenticated/login-protected sites**), discovers the site structure and sections, lets you select what to crawl, extracts structured facts and intelligence using Mistral AI, and stores everything into an **executable Python script (`.py`)**, **JSON (`.json`)**, and a **Markdown report (`.md`)**.

---

## What's New

1. **Authentication & Login Support**:
   - **Cookie-Based Auth**: Paste raw session cookie string from browser dev tools (or load a cookie file).
   - **Form-Based Login**: Automatically submits credentials to a login URL, auto-detects CSRF tokens, and preserves authenticated session cookies across the entire crawl.
   - **Bearer Token Auth**: Supports `Authorization: Bearer <token>` for token-based apps.
   - **HTTP Basic Auth**: Supports `username:password` basic authentication.
2. **Site Structure Discovery & Section Preview**:
   - Scans the starting website and categorizes internal links into logical sections (e.g. `/docs/`, `/products/`, `/blog/`).
   - Shows the total pages discovered, breakdown by section, and sample page titles before crawling.
   - Lets you choose:
     - **Crawl ALL discovered pages**
     - **Crawl top N pages**
     - **Crawl specific section(s)** (e.g. only `/docs/`)
     - **Crawl specific page number(s)** (e.g. `1, 3, 5-8`)
     - **Crawl single starting URL**

---

## How to Run

### 1. Guided Interactive Wizard
Run without arguments to be guided through site discovery, authentication, and selection:
```bash
python main.py
```

### 2. Preview Site Structure Without Crawling
Inspect the discovered sections and page count before making a decision:
```bash
python main.py --url https://books.toscrape.com --preview-only
```

### 3. Crawl Specific Pages by Numbers
Crawl selected pages from the discovery map (e.g. pages 1, 4, 7-10):
```bash
python main.py --url https://books.toscrape.com --pages 1,4
```

### 4. Authenticated Web Scraping

#### Form-based Login (Credentials + CSRF handling)
```bash
python main.py --url https://quotes.toscrape.com/ --login-url https://quotes.toscrape.com/login --username my_user --password my_pass --max-pages 5
```

#### Browser Cookie String
```bash
python main.py --url https://app.example.com/dashboard --cookie "sessionid=abc123xyz; auth_token=def456"
```

#### Bearer Token
```bash
python main.py --url https://api.example.com/docs --bearer "eyJhbGciOi..."
```

#### HTTP Basic Auth
```bash
python main.py --url https://staging.example.com --basic-auth "admin:secretpassword"
```

---

## Using the Stored Python Script

All extracted intelligence is written directly into an importable, executable Python script (`output/<site>_intelligence.py`):

```bash
python output/quotes_toscrape_com_intelligence.py
```

Or import it directly in any Python project:
```python
import sys
sys.path.append("output")

from quotes_toscrape_com_intelligence import (
    EXTRACTED_PAGES,
    get_all_key_facts,
    search_by_topic,
    get_all_contacts,
)

# Search pages by topic keyword
results = search_by_topic("quotes")

# Retrieve all key facts across the crawled pages
facts = get_all_key_facts()
for fact in facts:
    print("-", fact)
```

---

## Running Tests

Verify all components:
```bash
# Test URL normalization and filters
python test_urls.py

# Test Mistral LLM structured fact extraction
python test_llm.py

# Test Authentication Manager (Cookie, Bearer, Basic, and Form Login)
python test_auth.py
```

---

## Project Structure

```
website-tracker/
├── auth_manager.py      # Cookie, Bearer, Basic, and Form login with CSRF handling
├── crawler.py           # Site structure discovery, BFS queue, targeted crawl runner
├── fetcher.py           # HTTP requests with session persistence and browser headers
├── html_parser.py       # BeautifulSoup extraction of clean text, metadata, headings
├── url_manager.py       # Normalization, domain boundaries, and section classification
├── llm_extractor.py     # Mistral AI client with retry, model fallback, and schema extraction
├── storage.py           # Exporter for Python script (.py), JSON (.json), Markdown (.md)
├── main.py              # CLI and interactive user interface
├── test_auth.py         # Verification tests for authentication methods
├── test_llm.py          # Verification tests for LLM extraction
├── test_urls.py         # Verification tests for URL manager
├── output/              # Auto-generated .py, .json, and .md output files
├── .env                 # Environment variables (MISTRAL_API_KEY, AUTH_*)
└── requirements.txt     # Python dependencies
```
