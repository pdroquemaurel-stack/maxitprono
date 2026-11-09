from datetime import UTC, datetime

import pytest

from app.services.leagues import (CODE_ALPHABET, CODE_LENGTH, MAX_LEAGUES_PER_PLAYER,
                                  clean_color, clean_competition_ids, clean_name, create_error,
                                  format_code, gap_to_leader, generate_code, invite_from_next,
                                  join_error, league_trend, leave_error, normalize_code,
                                  rank_moves, ranking_preview, remove_error, standings,
                                  validate_league_name, week_extremes)
from app.services.ranking import PlayerScore
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
    ("Bureau Casa", None), ("abc", None), ("x" * 30, None), ("x" * 31, "error_league_name"),
    ("ab", "error_league_name"), ("   ab   ", "error_league_name"), ("x" * 41, "error_league_name"),
])
def test_validate_league_name(name, error):
    assert validate_league_name(name) == error


def test_create_refused_at_player_limit():
    assert create_error(MAX_LEAGUES_PER_PLAYER - 1) is None
    assert create_error(MAX_LEAGUES_PER_PLAYER) == "error_too_many_leagues"


def test_join_rules():
    assert join_error(False, 5, 0, max_members=100) is None
    assert join_error(True, 5, 0, max_members=100) == "error_already_member"
    assert join_error(False, 100, 0, max_members=100) == "error_league_full"
    assert join_error(False, 3, 0, max_members=3) == "error_league_full"  # limite réglée par l'admin
    assert join_error(False, 99, MAX_LEAGUES_PER_PLAYER, max_members=100) == "error_too_many_leagues"


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


# --- Refonte des écrans Ligues (lot 1) ---

def score(user_id, points, rank, nickname="X"):
    return PlayerScore(user_id, nickname, "CM", datetime(2026, 1, 1, tzinfo=UTC), points, 0, 0, rank)


def test_format_code_splits_in_two_groups_and_normalize_reads_it_back():
    assert format_code("K7PM4X") == "K7P-M4X"
    assert normalize_code(format_code("K7PM4X")) == "K7PM4X"


def test_clean_color_falls_back_to_orange():
    assert clean_color("green") == "green"
    assert clean_color("#123456") == "orange" and clean_color("") == "orange"


def test_clean_competition_ids():
    assert clean_competition_ids(["all", "3"], {3}) == []  # « Toutes » l'emporte
    assert clean_competition_ids([], {3}) == []
    assert clean_competition_ids(["3", "9", "x", "3"], {3, 4}) == [3]  # 9 : pas proposée


def test_rank_moves_up_down_same_and_newcomer():
    before = [score(1, 10, 1), score(2, 8, 2), score(3, 5, 3)]
    now = [score(2, 15, 1), score(1, 12, 2), score(3, 6, 3), score(4, 5, 4)]
    assert rank_moves(before, now) == {2: 1, 1: -1, 3: 0, 4: None}


def test_standings_appends_members_without_points():
    ranking = [score(1, 10, 1, "Awa")]
    rows = standings(ranking, [(2, "zoé"), (1, "Awa"), (3, "Bob")])
    assert [(r.user_id, r.rank) for r in rows] == [(1, 1), (3, 0), (2, 0)]


def test_week_extremes():
    assert week_extremes([]) == (None, None)
    solo = [score(1, 5, 1)]
    assert week_extremes(solo) == (solo[0], None)  # pas de lanterne rouge tout seul
    three = [score(1, 9, 1), score(2, 5, 2), score(3, 0, 3)]
    assert week_extremes(three) == (three[0], three[2])


def test_league_trend_sums_to_100_and_is_empty_without_picks():
    assert league_trend([]) is None
    assert league_trend([(2, 1)]) == (100, 0, 0)
    assert league_trend([(2, 1), (1, 1), (0, 3)]) == (34, 33, 33)
    assert sum(league_trend([(1, 0), (0, 0), (0, 0), (0, 2), (1, 3), (2, 2), (5, 0)])) == 100


def test_gap_to_leader():
    ranking = [score(1, 20, 1), score(2, 12, 2)]
    assert gap_to_leader(ranking, ranking[1]) == 8
    assert gap_to_leader(ranking, ranking[0]) == 0
    assert gap_to_leader(ranking, None) is None


def test_ranking_preview_adds_my_row_when_far_below():
    rest = [score(i, 0, i + 4) for i in range(20)]
    assert [r.user_id for r in ranking_preview(rest, me_id=2, limit=5)] == [0, 1, 2, 3, 4]
    assert [r.user_id for r in ranking_preview(rest, me_id=15, limit=5)] == [0, 1, 2, 3, 4, 15]


def test_invite_from_next():
    assert invite_from_next("/join/K7PM4X?ref=12") == ("K7PM4X", "12")
    assert invite_from_next("/j/K7P-M4X") == ("K7P-M4X", None)
    assert invite_from_next("/matches") is None
    assert invite_from_next("/join/K7PM4X/evil") is None
