from unittest.mock import MagicMock
from unittest.mock import patch

import requests

from core.controller_client import _aap_session
from core.controller_client import get_http_session
from core.controller_client import post


def _fake_response(status_code: int, payload: dict | list) -> requests.Response:
    """Return a Response-like mock that behaves for raise_for_status/json."""
    resp = MagicMock(spec=requests.Response)
    resp.status_code = status_code
    resp.json.return_value = payload

    if 400 <= status_code < 600:
        http_error = requests.HTTPError(response=resp)
        resp.raise_for_status.side_effect = http_error
    else:
        resp.raise_for_status.return_value = None
    return resp


def test_get_http_session_caches():
    """Subsequent calls without force_refresh must return the *same* object."""
    s1 = get_http_session()
    s2 = get_http_session()
    assert s1 is s2

    s3 = get_http_session(force_refresh=True)
    assert s3 is not s1 and s3 is _aap_session


@patch("core.controller_client.get_http_session")
def test_post_success(mock_get_http_session):
    session = MagicMock()
    session.post.return_value = _fake_response(201, {"id": 99})
    mock_get_http_session.return_value = session

    assert post("/labels/", {"name": "foo"}) == {"id": 99}
    session.post.assert_called_once()


@patch("core.controller_client.get_http_session")
def test_post_duplicate_name(mock_get_http_session):
    session = MagicMock()
    session.post.return_value = _fake_response(400, {"error": "duplicate"})
    session.get.return_value = _fake_response(200, {"results": [{"id": 42, "name": "foo"}]})
    mock_get_http_session.return_value = session

    out = post("/labels/", {"name": "foo"})
    assert out == {"id": 42, "name": "foo"}

    session.get.assert_called_once()
    session.post.assert_called_once()
