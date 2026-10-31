"""Strict URL allow-list to avoid fetching arbitrary hosts."""
from urllib.parse import urlparse

ALLOWED_HOSTS = {"facebook.com", "www.facebook.com", "m.facebook.com", "web.facebook.com", "fb.watch"}

def validate_facebook_url(value: str) -> str:
    if not value or len(value) > 4096:
        raise ValueError("A valid Facebook video URL is required.")
    parsed = urlparse(value.strip())
    if parsed.scheme not in {"http", "https"} or (parsed.hostname or "").lower() not in ALLOWED_HOSTS:
        raise ValueError("Only Facebook and fb.watch URLs are supported.")
    if parsed.username or parsed.password:
        raise ValueError("Credentials embedded in URLs are not accepted.")
    return value.strip()
