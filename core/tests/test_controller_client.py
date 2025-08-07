from unittest.mock import MagicMock
from unittest.mock import patch

import requests

import core.utils.controller.client as cc


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


def test_get_http_session():
    s1 = cc.get_http_session()
    s2 = cc.get_http_session()
    assert s1 is not s2


@patch("core.utils.controller.client.get_http_session")
def test_post_success(mock_get_http_session):
    session = MagicMock()
    session.post.return_value = _fake_response(201, {"id": 99})
    mock_get_http_session.return_value = session

    assert cc.post("/labels/", {"name": "foo"}) == {"id": 99}
    session.post.assert_called_once()


@patch("core.utils.controller.client.get_http_session")
def test_post_duplicate_name(mock_get_http_session):
    session = MagicMock()
    session.post.return_value = _fake_response(400, {"error": "duplicate"})
    session.get.return_value = _fake_response(
        200, {"results": [{"id": 42, "name": "foo"}]}
    )
    mock_get_http_session.return_value = session

    out = cc.post("/labels/", {"name": "foo"})
    assert out == {"id": 42, "name": "foo"}

    session.get.assert_called_once()
    session.post.assert_called_once()
