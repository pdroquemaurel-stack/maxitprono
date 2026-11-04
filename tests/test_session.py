from datetime import UTC, datetime, timedelta

from app.auth.session import SESSION_DURATION, read_session, sign_session

NOW = datetime(2026, 11, 4, 12, 0, tzinfo=UTC)
SECRET = "test-secret"


def test_signed_session_is_read_back():
    cookie = sign_session(42, NOW, SECRET)
    assert read_session(cookie, NOW, SECRET) == 42


def test_tampered_user_id_is_refused():
    cookie = sign_session(42, NOW, SECRET)
    forged = "1" + cookie[2:]  # on remplace 42 par 1
    assert read_session(forged, NOW, SECRET) is None


def test_other_secret_is_refused():
    cookie = sign_session(42, NOW, SECRET)
    assert read_session(cookie, NOW, "other-secret") is None


def test_expired_session_is_refused():
    cookie = sign_session(42, NOW, SECRET)
    later = NOW + SESSION_DURATION + timedelta(seconds=1)
    assert read_session(cookie, later, SECRET) is None


def test_missing_or_malformed_cookie():
    assert read_session(None, NOW, SECRET) is None
    assert read_session("", NOW, SECRET) is None
    assert read_session("abc", NOW, SECRET) is None
    assert read_session("a.b.c", NOW, SECRET) is None
