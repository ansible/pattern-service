import core.utils.controller.client as cc


def test_get_http_session():
    """Subsequent calls without force_refresh must return the *same* object."""
    s1 = cc.get_http_session()
    s2 = cc.get_http_session()
    assert s1 is not s2
