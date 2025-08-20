import logging
import urllib.parse
from typing import Any
from typing import Dict
from typing import Optional

import requests
from django.conf import settings
from requests import Session
from requests.auth import HTTPBasicAuth

from ..http_helpers import safe_json

logger = logging.getLogger(__name__)


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


def post(session: requests.Session, path: str, data: Dict) -> Dict[str, Any]:
    """
    Create a resource on the AAP controller.
    Args:
        session: Pre-existing session.
        path: Controller endpoint, e.g. "/projects/" (must include trailing slash).
        data: JSON payload to send.
    Returns:
        JSON for the created or pre‑existing object.
    Raises:
        requests.HTTPError
    """
    url = urllib.parse.urljoin(settings.AAP_URL, path)

    try:
        response = session.post(url, json=data)
        response.raise_for_status()
        return safe_json(lambda: response)()

    except requests.exceptions.HTTPError:
        raise
