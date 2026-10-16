"""
Authentication Manager module.
Handles multiple authentication methods for web scraping:
- Cookie-based authentication (raw cookie string, dictionary, or cookie file)
- Bearer Token / API Key header authentication
- HTTP Basic Authentication (username & password)
- Automated Form-based Login (submits login form with CSRF token detection and preserves session cookies)
"""

import json
import logging
import os
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlsplit
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import requests

load_dotenv()
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


def parse_cookie_string(cookie_str: str) -> dict[str, str]:
    """
    Parse a raw HTTP cookie header string into a key-value dictionary.
    Example: 'session_id=abc123; user=john; token=xyz' -> {'session_id': 'abc123', 'user': 'john', 'token': 'xyz'}
    """
    cookies = {}
    if not cookie_str or not cookie_str.strip():
        return cookies

    parts = cookie_str.split(";")
    for part in parts:
        part = part.strip()
        if "=" in part:
            key, val = part.split("=", 1)
            cookies[key.strip()] = val.strip()

    return cookies


def load_cookies_from_file(filepath: str | Path) -> dict[str, str]:
    """Load cookies from a JSON or text file."""
    path = Path(filepath)
    if not path.is_file():
        raise FileNotFoundError(f"Cookie file not found: {filepath}")

    content = path.read_text(encoding="utf-8").strip()

    # Try JSON format first (e.g. exported from browser extensions)
    if content.startswith("{") or content.startswith("["):
        try:
            data = json.loads(content)
            if isinstance(data, dict):
                return {str(k): str(v) for k, v in data.items()}
            elif isinstance(data, list):
                # Standard browser cookie export format [{name: '...', value: '...'}, ...]
                return {item["name"]: item["value"] for item in data if "name" in item and "value" in item}
        except Exception:
            pass

    # Fallback to key=value string format
    return parse_cookie_string(content)


def extract_form_inputs(soup: BeautifulSoup, form_tag: Any) -> dict[str, str]:
    """Extract all input values (including hidden CSRF tokens) from a form element."""
    inputs = {}
    for input_tag in form_tag.find_all("input"):
        name = input_tag.get("name")
        if name:
            inputs[name] = input_tag.get("value", "")
    return inputs


def perform_form_login(
    session: requests.Session,
    login_url: str,
    username: str,
    password: str,
    username_field: str | None = None,
    password_field: str | None = None,
    timeout: int = 15,
) -> bool:
    """
    Perform automated form-based login:
    1. GET the login page to acquire initial cookies and CSRF tokens.
    2. Detect form action and input field names (csrf, username/email, password).
    3. POST the credentials and CSRF tokens.
    4. Validate whether session cookies were received or login redirected.
    """
    print(f"\n[Auth] Fetching login page: {login_url}")
    get_res = session.get(login_url, timeout=timeout, allow_redirects=True)
    get_res.raise_for_status()

    soup = BeautifulSoup(get_res.text, "html.parser")
    form = soup.find("form")
    if not form:
        raise ValueError(f"No login <form> found on {login_url}")

    # Determine form action URL
    action = form.get("action", "")
    post_url = urljoin(login_url, action) if action else login_url

    # Extract all existing form fields (especially hidden CSRF tokens)
    form_data = extract_form_inputs(soup, form)

    # Detect username / email field if not specified
    if not username_field:
        candidates = ["username", "user", "email", "login", "user[email]", "user_login", "account", "id"]
        for cand in candidates:
            if cand in form_data or form.find("input", attrs={"name": cand}) or form.find("input", attrs={"id": cand}):
                username_field = cand
                break
        if not username_field:
            # Pick first text or email input
            text_input = form.find("input", attrs={"type": ["text", "email"]})
            if text_input and text_input.get("name"):
                username_field = text_input["name"]
            else:
                username_field = "username"

    # Detect password field if not specified
    if not password_field:
        candidates = ["password", "pass", "pwd", "user[password]", "user_password"]
        for cand in candidates:
            if cand in form_data or form.find("input", attrs={"name": cand}):
                password_field = cand
                break
        if not password_field:
            pwd_input = form.find("input", attrs={"type": "password"})
            if pwd_input and pwd_input.get("name"):
                password_field = pwd_input["name"]
            else:
                password_field = "password"

    form_data[username_field] = username
    form_data[password_field] = password

    print(f"[Auth] Submitting login credentials to: {post_url}")
    print(f"       Username field: '{username_field}' | Password field: '{password_field}'")

    post_headers = {
        "Referer": login_url,
        "Origin": f"{urlsplit(login_url).scheme}://{urlsplit(login_url).netloc}",
    }

    post_res = session.post(
        post_url,
        data=form_data,
        headers=post_headers,
        timeout=timeout,
        allow_redirects=True,
    )

    cookies_count = len(session.cookies)
    print(f"[Auth] Login response status: {post_res.status_code} | Cookies stored: {cookies_count}")

    # Inspect response for obvious failure messages
    lower_text = post_res.text.lower()
    failure_indicators = [
        "invalid username or password",
        "invalid credentials",
        "incorrect password",
        "authentication failed",
        "login failed",
    ]
    for fail_msg in failure_indicators:
        if fail_msg in lower_text:
            print(f"[!] Warning: Login response text indicates failure: '{fail_msg}'")
            return False

    return True


def create_authenticated_session(
    auth_type: str = "none",
    cookie_str: str | None = None,
    cookie_file: str | None = None,
    bearer_token: str | None = None,
    custom_headers: dict[str, str] | None = None,
    basic_auth: tuple[str, str] | None = None,
    login_url: str | None = None,
    username: str | None = None,
    password: str | None = None,
    username_field: str | None = None,
    password_field: str | None = None,
) -> requests.Session:
    """
    Build a configured requests.Session with specified credentials / headers / cookies.
    """
    session = requests.Session()
    session.headers.update(DEFAULT_HEADERS)

    if custom_headers:
        session.headers.update(custom_headers)

    # 1. Check environment variables if auth not explicitly passed
    if auth_type == "none":
        if os.getenv("AUTH_COOKIE"):
            auth_type = "cookie"
            cookie_str = os.getenv("AUTH_COOKIE")
        elif os.getenv("AUTH_BEARER_TOKEN"):
            auth_type = "bearer"
            bearer_token = os.getenv("AUTH_BEARER_TOKEN")
        elif os.getenv("AUTH_LOGIN_URL") and os.getenv("AUTH_USERNAME") and os.getenv("AUTH_PASSWORD"):
            auth_type = "login_form"
            login_url = os.getenv("AUTH_LOGIN_URL")
            username = os.getenv("AUTH_USERNAME")
            password = os.getenv("AUTH_PASSWORD")

    # 2. Cookie Authentication
    if auth_type == "cookie" or cookie_str or cookie_file:
        cookies_dict = {}
        if cookie_file:
            cookies_dict.update(load_cookies_from_file(cookie_file))
        if cookie_str:
            cookies_dict.update(parse_cookie_string(cookie_str))

        if cookies_dict:
            session.cookies.update(cookies_dict)
            print(f"[Auth] Configured {len(cookies_dict)} session cookies.")

    # 3. Bearer Token Authentication
    elif auth_type == "bearer" or bearer_token:
        token = (bearer_token or "").strip()
        if not token.lower().startswith("bearer "):
            token = f"Bearer {token}"
        session.headers["Authorization"] = token
        print("[Auth] Configured Bearer Authorization header.")

    # 4. HTTP Basic Auth
    elif auth_type == "basic" or basic_auth:
        if basic_auth:
            session.auth = basic_auth
            print(f"[Auth] Configured HTTP Basic Auth for user '{basic_auth[0]}'.")

    # 5. Form-based Login
    elif auth_type == "login_form" or (login_url and username and password):
        if not login_url or not username or not password:
            raise ValueError("Form login requires login_url, username, and password.")
        success = perform_form_login(
            session=session,
            login_url=login_url,
            username=username,
            password=password,
            username_field=username_field,
            password_field=password_field,
        )
        if not success:
            print("[!] Warning: Form login may have failed. Proceeding with collected session state.")

    return session

