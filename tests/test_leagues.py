import pytest

from app.services.leagues import (CODE_ALPHABET, CODE_LENGTH, MAX_LEAGUES_PER_PLAYER,
                                  MAX_MEMBERS, clean_name, create_error, generate_code,
                                  join_error, leave_error, normalize_code, remove_error,
                                  validate_league_name)
from app.services.redirects import safe_next


def test_generated_code_avoids_look_alike_characters():
    for _ in range(200):
        code = generate_code()
        assert len(code) == CODE_LENGTH
        assert set(code) <= set(CODE_ALPHABET)
    assert not set("0O1IL") & set(CODE_ALPHABET)


@pytest.mark.parametrize("typed, expected", [
    ("K7PM4X", "K7PM4X"), ("k7pm4x", "K7PM4X"), (" k7p m4x ", "K7PM4X"), ("K7P-M4X", "K7PM4X"),
])
def test_normalize_code(typed, expected):
    assert normalize_code(typed) == expected


def test_clean_name_collapses_spaces():
    assert clean_name("  Bureau   Casa ") == "Bureau Casa"


@pytest.mark.parametrize("name, error", [
    ("Bureau Casa", None), ("abc", None), ("x" * 40, None),
    ("ab", "error_league_name"), ("   ab   ", "error_league_name"), ("x" * 41, "error_league_name"),
])
def test_validate_league_name(name, error):
    assert validate_league_name(name) == error


def test_create_refused_at_player_limit():
    assert create_error(MAX_LEAGUES_PER_PLAYER - 1) is None
    assert create_error(MAX_LEAGUES_PER_PLAYER) == "error_too_many_leagues"


def test_join_rules():
    assert join_error(False, 5, 0) is None
    assert join_error(True, 5, 0) == "error_already_member"
    assert join_error(False, MAX_MEMBERS, 0) == "error_league_full"
    assert join_error(False, MAX_MEMBERS - 1, MAX_LEAGUES_PER_PLAYER) == "error_too_many_leagues"


def test_owner_cannot_leave_but_members_can():
    assert leave_error(is_owner=True) == "error_owner_cannot_leave"
    assert leave_error(is_owner=False) is None


def test_only_owner_removes_and_not_himself():
    assert remove_error(is_owner=True, target_is_owner=False) is None
    assert remove_error(is_owner=False, target_is_owner=False) == "error_not_league_owner"
    assert remove_error(is_owner=True, target_is_owner=True) == "error_owner_cannot_leave"


@pytest.mark.parametrize("value, expected", [
    ("/join/K7PM4X", "/join/K7PM4X"), ("/profile", "/profile"),
    (None, "/"), ("", "/"), ("https://evil.example", "/"), ("//evil.example", "/"),
    ("/\\evil.example", "/"), ("join", "/"),
])
def test_safe_next(value, expected):
    assert safe_next(value) == expected
