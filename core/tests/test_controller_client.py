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


@patch("core.utils.controller.client.get_http_session")
def test_post_non_400_error_is_propagated(mock_get_http_session):
    session = MagicMock()
    session.post.return_value = _fake_response(500, {"error": "server"})
    mock_get_http_session.return_value = session

    with pytest.raises(requests.HTTPError):
        cc.post("/labels/", {"name": "foo"})

    # Ensure we don't try to deduplicate
    session.get.assert_not_called()


@patch("core.utils.controller.client.get_http_session")
def test_post_400_dedupe_no_results_raises(mock_get_http_session):
    session = MagicMock()
    post_resp = _fake_response(400, {"detail": "duplicate"})
    session.post.return_value = post_resp
    session.get.return_value = _fake_response(200, {"results": []})
    mock_get_http_session.return_value = session

    with pytest.raises(requests.HTTPError) as exc:
        cc.post("/labels/", {"name": "foo", "organization": 1})

    assert isinstance(exc.value, requests.HTTPError)
    assert exc.value.response.status_code == 400
    session.get.assert_called_once()
    # Ensure params include both default dedupe keys
    _, kwargs = session.get.call_args
    assert kwargs["params"] == {"name": "foo", "organization": 1}


@patch("core.utils.controller.client.get_http_session")
def test_post_400_dedupe_lookup_http_error_still_raises(mock_get_http_session):
    session = MagicMock()
    session.post.return_value = _fake_response(400, {"detail": "duplicate"})
    # Lookup GET itself errors (e.g., 404)
    session.get.return_value = _fake_response(404, {"detail": "not found"})
    mock_get_http_session.return_value = session

    with pytest.raises(requests.HTTPError):
        cc.post("/labels/", {"name": "foo"})

    session.get.assert_called_once()


@patch("core.utils.controller.client.get_http_session")
def test_post_400_dedupe_params_subset_when_missing_org(mock_get_http_session):
    session = MagicMock()
    session.post.return_value = _fake_response(400, {"detail": "duplicate"})
    session.get.return_value = _fake_response(200, {"results": []})
    mock_get_http_session.return_value = session

    with pytest.raises(requests.HTTPError):
        cc.post("/labels/", {"name": "foo"})

    # Only 'name' present in params, no 'organization' since it wasn’t provided
    _, kwargs = session.get.call_args
    assert kwargs["params"] == {"name": "foo"}


@patch("core.utils.controller.client.get_http_session")
def test_post_400_with_custom_dedupe_keys(mock_get_http_session):
    session = MagicMock()
    session.post.return_value = _fake_response(400, {"detail": "duplicate"})
    session.get.return_value = _fake_response(200, {"results": []})
    mock_get_http_session.return_value = session

    with pytest.raises(requests.HTTPError):
        cc.post(
            "/labels/",
            {"name": "foo", "organization": 1, "extra": "x"},
            dedupe_keys=("name", "extra"),
        )

    # Only custom keys should be used
    _, kwargs = session.get.call_args
    assert kwargs["params"] == {"name": "foo", "extra": "x"}


@patch("core.utils.controller.client.get_http_session")
def test_post_400_error_json_fallback_to_text(mock_get_http_session):
    session = MagicMock()
    # Create a response whose .json() raises, forcing fallback to .text
    resp = MagicMock(spec=requests.Response)
    resp.status_code = 400
    resp.text = "not json"
    resp.json.side_effect = Exception("bad json")
    resp.raise_for_status.side_effect = requests.HTTPError(response=resp)
    session.post.return_value = resp
    session.get.return_value = _fake_response(200, {"results": []})
    mock_get_http_session.return_value = session

    with pytest.raises(requests.HTTPError) as exc:
        cc.post("/labels/", {"name": "foo"})

    # Error message should include the fallback text
    assert "not json" in str(exc.value)
