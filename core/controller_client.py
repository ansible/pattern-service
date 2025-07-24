import logging
from typing import Dict
from typing import Iterator
from typing import Optional

import requests
from requests import Session
from requests.auth import HTTPBasicAuth

from pattern_service.settings.aap import get_aap_settings

logger = logging.getLogger(__name__)

settings = get_aap_settings()

_aap_session: Optional[Session] = None


def get_http_session(force_refresh: bool = False) -> Session:
    """Returns a cached Session instance with AAP credentials."""
    global _aap_session
    if _aap_session is None or force_refresh:
        session = Session()
        session.auth = HTTPBasicAuth(settings.username, settings.password)
        session.verify = settings.verify_ssl
        session.headers.update({'Content-Type': 'application/json'})
        _aap_session = session

    return _aap_session


def get(path: str, *, params: Optional[Dict] = None) -> requests.Response:
    session = get_http_session()
    url = f"{settings.url}{path}"
    response = session.get(url, params=params, stream=True)
    response.raise_for_status()

    return response
