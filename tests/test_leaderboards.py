from datetime import UTC, datetime, timedelta

import pytest

from app.models import Competition, Match, Prediction, User
from app.models.match import MatchStatus
from app.services.leaderboards import leaderboard
from app.services.ranking import week_bounds

MONDAY = datetime(2026, 11, 2, 18, 0, tzinfo=UTC)


@pytest.fixture
def world(db):
    """Deux compétitions, trois joueurs (2 au Cameroun, 1 au Burkina)."""
    ligue1 = Competition(provider="api_football", external_id="61", name="Ligue 1", is_active=True)
    can = Competition(provider="api_football", external_id="6", name="CAN", is_active=True)
    users = [User(nickname=n, nickname_key=n.lower(), pin_hash="x", country_code=c,
                  rules_accepted_at=MONDAY, created_at=MONDAY + timedelta(minutes=i))
             for i, (n, c) in enumerate([("Ali", "CM"), ("Bea", "CM"), ("Cyr", "BF")])]
    db.add_all([ligue1, can, *users])
    db.commit()
    return {"ligue1": ligue1, "can": can, "users": users}


def add_scored(db, user, competition, points, kickoff=MONDAY, exact=False, winner=None):
    match = Match(competition=competition, home_team="A", away_team="B", kickoff_at=kickoff,
                  status=MatchStatus.FINISHED, home_score=1, away_score=0)
    db.add(match)
    db.flush()
    db.add(Prediction(user_id=user.id, match_id=match.id, home_score=1, away_score=0,
                      points=points, is_exact=exact,
                      is_winner=points > 0 if winner is None else winner))
    db.commit()


def nicknames(ranking):
    return [p.nickname for p in ranking]


def test_general_ranking_sums_points_and_counts(db, world):
    ali, bea, cyr = world["users"]
    add_scored(db, ali, world["ligue1"], 5, exact=True)
    add_scored(db, ali, world["ligue1"], 3)
    add_scored(db, bea, world["ligue1"], 0)
    add_scored(db, cyr, world["can"], 5, exact=True)

    ranking = leaderboard(db)

    assert nicknames(ranking) == ["Ali", "Cyr", "Bea"]
    assert (ranking[0].points, ranking[0].exacts, ranking[0].winners) == (8, 1, 2)
    assert ranking[2].points == 0


def test_tie_broken_by_exacts_in_sql(db, world):
    ali, bea, _ = world["users"]
    for _ in range(5):
        add_scored(db, ali, world["ligue1"], 3)  # 5 bons vainqueurs = 15 points
    for _ in range(3):
        add_scored(db, bea, world["ligue1"], 5, exact=True)  # 3 scores exacts = 15 points

    assert nicknames(leaderboard(db)) == ["Bea", "Ali"]


def test_player_without_scored_prediction_is_not_ranked(db, world):
    ali, bea, _ = world["users"]
    add_scored(db, ali, world["ligue1"], 3)
    match = Match(competition=world["ligue1"], home_team="A", away_team="B", kickoff_at=MONDAY,
                  status=MatchStatus.CANCELLED)
    db.add(match)
    db.flush()
    db.add(Prediction(user_id=bea.id, match_id=match.id, home_score=1, away_score=1))
    db.commit()

    assert nicknames(leaderboard(db)) == ["Ali"]


def test_filter_by_country(db, world):
    ali, _, cyr = world["users"]
    add_scored(db, ali, world["ligue1"], 3)
    add_scored(db, cyr, world["ligue1"], 5)
    assert nicknames(leaderboard(db, country_code="BF")) == ["Cyr"]


def test_filter_by_competition(db, world):
    ali, _, cyr = world["users"]
    add_scored(db, ali, world["ligue1"], 3)
    add_scored(db, cyr, world["can"], 5)
    add_scored(db, cyr, world["ligue1"], 0)
    ranking = leaderboard(db, competition_id=world["ligue1"].id)
    assert nicknames(ranking) == ["Ali", "Cyr"]
    assert ranking[1].points == 0


def test_filter_by_week(db, world):
    ali, bea, _ = world["users"]
    add_scored(db, ali, world["ligue1"], 3, kickoff=MONDAY)
    add_scored(db, bea, world["ligue1"], 5, kickoff=MONDAY + timedelta(days=7))  # semaine suivante
    sunday_night = datetime(2026, 11, 8, 23, 30, tzinfo=UTC)
    add_scored(db, bea, world["ligue1"], 1, kickoff=sunday_night)

    ranking = leaderboard(db, period=week_bounds(MONDAY.date()))

    assert nicknames(ranking) == ["Ali", "Bea"]
    assert ranking[1].points == 1
