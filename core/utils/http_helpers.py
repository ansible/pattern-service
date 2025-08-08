import logging
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


def validate_url(url: str) -> str:
    """Ensure the URL has a valid scheme and format."""
    if not url.startswith(("http://", "https://")):
        url = f"http://{url}"
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        raise ValueError(f"Invalid URL: {url}")
    return url.rstrip("/")
