
from url_manager import (
    normalize_url,
    is_allowed_url,
    get_internal_links,
)

start = "https://example.com/"


# Test 1: Relative URL
assert normalize_url(
    "/about",
    base_url=start,
) == "https://example.com/about"


# Test 2: Fragment removal
assert normalize_url(
    "https://example.com/about#team"
) == "https://example.com/about"


# Test 3: External website
assert not is_allowed_url(
    "https://google.com/",
    start,
)


# Test 4: Unsupported scheme
assert normalize_url("javascript:alert(1)") is None


# Test 5: Duplicate links
links = [
    {"href": "/about"},
    {"href": "https://example.com/about#team"},
    {"href": "https://google.com/"},
]

result = get_internal_links(
    links,
    current_url=start,
    start_url=start,
)

assert result == ["https://example.com/about"]

print("All URL manager tests passed!")
