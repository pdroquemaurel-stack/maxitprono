from datetime import UTC, datetime, timedelta

import pytest

from app.services.accounts import (
    LOCK_DURATION,
    MAX_AVATAR_BYTES,
    after_failed_attempt,
    avatar_mime,
    decode_data_url,
    hash_pin,
    is_locked,
    nickname_key,
    validate_country,
    validate_nickname,
    validate_pin,
    verify_pin,
)

NOW = datetime(2026, 11, 4, 12, 0, tzinfo=UTC)


@pytest.mark.parametrize("nickname", ["Paul", "abc", "Lion_237", "a-b-c", "x" * 20])
def test_valid_nicknames(nickname):
    assert validate_nickname(nickname) is None


@pytest.mark.parametrize("nickname", ["", "ab", "x" * 21, "Paul R", "émile", "a.b", "<b>"])
def test_invalid_nicknames(nickname):
    assert validate_nickname(nickname) == "error_nickname_format"


def test_nickname_key_ignores_case_and_spaces():
    assert nickname_key(" Paul ") == nickname_key("PAUL") == "paul"


@pytest.mark.parametrize("pin", ["0000", "1234", "9876"])
def test_valid_pins(pin):
    assert validate_pin(pin) is None


@pytest.mark.parametrize("pin", ["", "123", "12345", "12a4", " 1234", "１２３４"])
def test_invalid_pins(pin):
    assert validate_pin(pin) == "error_pin_format"


def test_validate_country():
    assert validate_country("CM", {"CM", "BF"}) is None
    assert validate_country("XX", {"CM", "BF"}) == "error_country"


def test_hash_pin_is_salted_and_verifiable():
    first, second = hash_pin("1234"), hash_pin("1234")
    assert first != second  # sel différent à chaque fois
    assert "1234" not in first
    assert verify_pin("1234", first)
    assert verify_pin("1234", second)
    assert not verify_pin("1235", first)


def test_verify_pin_rejects_malformed_hash():
    assert not verify_pin("1234", "n-importe-quoi")


def test_is_locked():
    assert not is_locked(None, NOW)
    assert is_locked(NOW + timedelta(seconds=1), NOW)
    assert not is_locked(NOW, NOW)
    assert not is_locked(NOW - timedelta(minutes=1), NOW)


def test_four_failures_do_not_lock():
    count, locked_until = 0, None
    for _ in range(4):
        count, locked_until = after_failed_attempt(count, NOW)
    assert count == 4
    assert locked_until is None


def test_fifth_failure_locks_for_15_minutes_and_resets_counter():
    count, locked_until = after_failed_attempt(4, NOW)
    assert count == 0
    assert locked_until == NOW + LOCK_DURATION


JPEG = b"\xff\xd8\xff\xe0" + b"0" * 100
PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 100


def test_avatar_mime_accepts_jpeg_and_png():
    assert avatar_mime(JPEG) == ("image/jpeg", None)
    assert avatar_mime(PNG) == ("image/png", None)


def test_avatar_mime_refuses_other_files():
    assert avatar_mime(b"GIF89a...") == (None, "error_avatar_format")
    assert avatar_mime(b"<svg></svg>") == (None, "error_avatar_format")


def test_avatar_mime_refuses_big_files():
    assert avatar_mime(JPEG + b"0" * MAX_AVATAR_BYTES) == (None, "error_avatar_too_big")


def test_decode_data_url():
    assert decode_data_url("data:image/jpeg;base64,/9j/4A==") == b"\xff\xd8\xff\xe0"
    assert decode_data_url("data:image/jpeg;base64,!!!") is None
    assert decode_data_url("") is None
