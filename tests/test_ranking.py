from datetime import UTC, date, datetime

from app.services.ranking import PlayerScore, find_player, rank_players, week_bounds, week_start

EARLY = datetime(2026, 1, 1, tzinfo=UTC)
LATE = datetime(2026, 6, 1, tzinfo=UTC)


def player(user_id, points=0, exacts=0, winners=0, created_at=EARLY):
    return PlayerScore(user_id, f"p{user_id}", "CM", created_at, points, exacts, winners)


def ranked_ids(players):
    return [p.user_id for p in rank_players(players)]


def test_more_points_ranks_first():
    assert ranked_ids([player(1, points=3), player(2, points=8), player(3, points=5)]) == [2, 3, 1]


def test_tie_on_points_broken_by_exact_scores():
    assert ranked_ids([player(1, points=10, exacts=1), player(2, points=10, exacts=2)]) == [2, 1]


def test_tie_on_exacts_broken_by_winners():
    players = [player(1, points=10, exacts=1, winners=2), player(2, points=10, exacts=1, winners=3)]
    assert ranked_ids(players) == [2, 1]


def test_full_tie_broken_by_oldest_registration():
    players = [player(1, 10, 1, 3, created_at=LATE), player(2, 10, 1, 3, created_at=EARLY)]
    assert ranked_ids(players) == [2, 1]


def test_ranks_are_consecutive_and_distinct():
    ranking = rank_players([player(1, 5), player(2, 5), player(3, 0)])
    assert [p.rank for p in ranking] == [1, 2, 3]


def test_find_player():
    ranking = rank_players([player(1, 5), player(2, 9)])
    assert find_player(ranking, 1).rank == 2
    assert find_player(ranking, 42) is None


def test_week_runs_monday_to_sunday():
    assert week_start(date(2026, 11, 4)) == date(2026, 11, 2)  # mercredi -> lundi
    assert week_start(date(2026, 11, 2)) == date(2026, 11, 2)
    assert week_start(date(2026, 11, 8)) == date(2026, 11, 2)  # dimanche
    start, end = week_bounds(date(2026, 11, 2))
    assert start == datetime(2026, 11, 2, tzinfo=UTC)
    assert end == datetime(2026, 11, 9, tzinfo=UTC)
