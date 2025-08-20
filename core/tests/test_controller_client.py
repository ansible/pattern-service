from unittest.mock import MagicMock
from unittest.mock import patch

import pytest
import requests

import core.utils.controller.client as cc


def test_get_http_session():
    """Subsequent calls without force_refresh must not return the *same* object."""
    s1 = cc.get_http_session()
    s2 = cc.get_http_session()
    assert s1 is not s2


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


@patch("core.utils.controller.client.get_http_session")
def test_post_non_400_error_is_propagated(mock_get_http_session):
    """
    Test that a non-400 error is also immediately propagated.
    """
    session = MagicMock()
    session.post.return_value = _fake_response(500, {"error": "server"})
    mock_get_http_session.return_value = session

    with pytest.raises(requests.HTTPError):
        cc.post(session, "/labels/", {"name": "foo"})

    session.get.assert_not_called()
    session.post.assert_called_once()


@patch("core.utils.controller.client.get_http_session")
def test_post_success(mock_get_http_session):
    """
    Test that a successful POST request returns the JSON response.
    """
    session = MagicMock()
    session.post.return_value = _fake_response(201, {"id": 123, "name": "foo"})
    mock_get_http_session.return_value = session

    out = cc.post(session, "/labels/", {"name": "foo"})
    assert out == {"id": 123, "name": "foo"}

    session.get.assert_not_called()
    session.post.assert_called_once()
