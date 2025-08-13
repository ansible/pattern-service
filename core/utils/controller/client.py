import json
import logging
import urllib.parse
from typing import Any
from typing import Callable
from typing import Dict
from typing import Optional
from typing import Sequence
from typing import TypeVar

import requests
from django.conf import settings
from requests import Session
from requests.auth import HTTPBasicAuth

from ..http_helpers import safe_json

logger = logging.getLogger(__name__)


F = TypeVar("F", bound=Callable[..., requests.Response])


def get_http_session() -> Session:
    """Creates and returns a new Session instance with AAP credentials."""
    session = Session()
    session.auth = HTTPBasicAuth(settings.AAP_USERNAME, settings.AAP_PASSWORD)
    session.verify = settings.AAP_VALIDATE_CERTS
    session.headers.update({"Content-Type": "application/json"})
    return session


def get(url: str, *, params: Optional[Dict] = None) -> requests.Response:
    with get_http_session() as session:
        response = session.get(url, params=params, stream=True)
        response.raise_for_status()
        return response


def post(
    path: str,
    data: Dict,
    *,
    dedupe_keys: Sequence[str] = ("name", "organization"),
) -> Dict[str, Any]:
    """
    Create a resource on the AAP controller.
    If the POST fails with 400 because the object already exists,
    perform a GET lookup using *dedupe_keys* taken from *data* and
    return the existing object instead.
    Args:
        path: Controller endpoint, e.g. "/projects/" (must include trailing slash).
        data: JSON payload to send.
        dedupe_keys: Keys from *data* to copy into the lookup query string when handling
            a duplicate‑name error.
    Returns:
        JSON for the created or pre‑existing object.
    Raises:
        requests.HTTPError
            Propagated if the status code is not a handled 400 or if the lookup
            returns no result.
    """
    session = get_http_session()
    url = urllib.parse.urljoin(settings.AAP_URL, path)
    try:
        response = session.post(url, json=data)
        response.raise_for_status()

        # Safely parse response JSON
        return safe_json(lambda: response)()

    except requests.exceptions.HTTPError as exc:
        response = exc.response
        if response.status_code != 400:
            raise

        try:
            error_json = safe_json(lambda: response)()
        except Exception:
            error_json = {"detail": response.text}

        logger.warning(f"AAP POST {url} failed with 400. Error response: {error_json}")
        logger.debug(f"Payload sent: {json.dumps(data, indent=2)}")
        logger.debug(f"AAP POST {url} 400; dedup lookup keys: {dedupe_keys}")

        # Attempt deduplication if resource already exists
        params = {k: data[k] for k in dedupe_keys if k in data}
        try:
            lookup_resp = session.get(url, params=params)
            lookup_resp.raise_for_status()
            results = safe_json(lambda: lookup_resp)().get("results", [])

            if results:
                logger.debug(
                    f"Resource already exists. Returning existing resource: {results[0]}"
                )
                return results[0]
        except Exception as e:
            logger.debug(
                f"Deduplication GET failed for {url} with params {params}: {e}"
            )

        # If dedupe fails or no match found, raise with full detail
        raise requests.HTTPError(
            f"400 Bad Request for {url}.\n"
            f"Payload: {json.dumps(data, indent=2)}\n"
            f"Response: {json.dumps(error_json, indent=2)}",
            response=response,
        )
