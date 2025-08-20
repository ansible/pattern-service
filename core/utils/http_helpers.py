import logging
from functools import wraps
from typing import Any
from typing import Callable
from typing import Optional
from typing import TypeVar
from urllib.parse import urlparse

import requests

logger = logging.getLogger(__name__)


F = TypeVar("F", bound=Callable[..., requests.Response])


class RetryError(Exception):
    """Custom exception raised when a retry limit is reached."""

    def __init__(
        self, msg: str, request: Optional[Any] = None, response: Optional[Any] = None
    ) -> None:
        super().__init__(msg)
        self.request = request
        self.response = response


def safe_json(func: F) -> Callable[..., dict[str, Any]]:
    """
    Decorator for functions that return a `requests.Response`.
    It attempts to parse JSON safely and falls back to raw text if needed.
    """

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> dict[str, Any]:
        response = func(*args, **kwargs)
        try:
            return response.json()  # type: ignore[no-any-return]
        except ValueError:
            logger.warning(f"Non-JSON response from {response.url}: {response.text!r}")
            return {
                "detail": "Non-JSON response",
                "text": response.text,
                "status_code": response.status_code,
                "url": response.url,
            }

    return wrapper


def validate_url(url: str) -> str:
    """Ensure the URL has a valid scheme and format."""
    if not url.startswith(("http://", "https://")):
        url = f"http://{url}"
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        raise ValueError(f"Invalid URL: {url}")
    return url.rstrip("/")
