from core.controller_client import _aap_session
from core.controller_client import get_http_session


def test_get_http_session_caches():
    """Subsequent calls without force_refresh must return the *same* object."""
    s1 = get_http_session()
    s2 = get_http_session()
    assert s1 is s2

    s3 = get_http_session(force_refresh=True)
    assert s3 is not s1 and s3 is _aap_session
