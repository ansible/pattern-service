import core.controller_client as cc

def test_get_http_session_caches():
    """Subsequent calls without force_refresh must return the *same* object."""
    s1 = cc.get_http_session()
    s2 = cc.get_http_session()
    assert s1 is s2

    s3 = cc.get_http_session(force_refresh=True)
    assert s3 is not s1 and s3 is cc._aap_session
