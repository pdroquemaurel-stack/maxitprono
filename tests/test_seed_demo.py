import random
from datetime import UTC, datetime

from app.models import Competition, Match, Prediction, User
from app.models.match import MatchStatus
from app.services.leaderboards import leaderboard
from scripts.seed_demo import (PAST_COUNT, UPCOMING_COUNT, finish_open_matches, reset,
                               seed)

NOW = datetime(2026, 11, 4, 12, 0, tzinfo=UTC)


def open_matches(db):
    return db.query(Match).filter(Match.status == MatchStatus.SCHEDULED,
                                  Match.kickoff_at > NOW).all()


def test_seed_creates_players_matches_and_a_ranking(db):
    result = seed(db, NOW, random.Random(1))

    assert result["players"] == 6
    assert len(open_matches(db)) == UPCOMING_COUNT
    assert all(m.external_id is None for m in db.query(Match))  # jamais touchés par l'import
    assert len(leaderboard(db)) == 6


def test_seed_twice_creates_no_duplicates(db):
    seed(db, NOW, random.Random(1))
    second = seed(db, NOW, random.Random(2))

    assert second == {"players": 6, "past": 0, "upcoming": 0, "predicted": UPCOMING_COUNT,
                      "scored": second["scored"]}
    assert db.query(Prediction).count() == 6 * (PAST_COUNT + UPCOMING_COUNT)  # aucun doublon
    assert db.query(User).count() == 6


def test_finish_scores_real_player_prediction(db):
    seed(db, NOW, random.Random(1))
    paul = User(nickname="Paul", nickname_key="paul", pin_hash="x", country_code="CM",
                rules_accepted_at=NOW)
    db.add(paul)
    db.commit()
    match = open_matches(db)[0]
    db.add(Prediction(user_id=paul.id, match_id=match.id, home_score=1, away_score=0))
    db.commit()

    assert finish_open_matches(db, NOW, random.Random(1)) == UPCOMING_COUNT

    assert open_matches(db) == []
    prediction = db.query(Prediction).filter_by(user_id=paul.id).one()
    assert prediction.points is not None
    assert any(p.nickname == "Paul" for p in leaderboard(db))


def test_reset_removes_only_demo_data(db):
    real = Competition(provider="api_football", external_id="61", name="Ligue 1")
    paul = User(nickname="Paul", nickname_key="paul", pin_hash="x", country_code="CM",
                rules_accepted_at=NOW)
    db.add_all([real, paul])
    db.commit()
    seed(db, NOW, random.Random(1))
    demo_match = open_matches(db)[0]
    db.add(Prediction(user_id=paul.id, match_id=demo_match.id, home_score=1, away_score=0))
    db.commit()

    reset(db)

    assert [u.nickname for u in db.query(User)] == ["Paul"]
    assert [c.name for c in db.query(Competition)] == ["Ligue 1"]
    assert db.query(Match).count() == 0 and db.query(Prediction).count() == 0


def test_demo_players_predict_open_matches_of_active_competitions(db):
    from datetime import timedelta

    from app.services.probabilities import MIN_PREDICTIONS_FOR_TRENDS
    real = Competition(provider="football_data", external_id="FL1", name="Ligue 1", is_active=True)
    hidden = Competition(provider="football_data", external_id="PL", name="PL", is_active=False)
    open_real = Match(competition=real, home_team="PSG", away_team="OM",
                      kickoff_at=NOW + timedelta(days=1))
    closed_real = Match(competition=real, home_team="Lens", away_team="Lille",
                        kickoff_at=NOW + timedelta(minutes=5))
    inactive = Match(competition=hidden, home_team="A", away_team="B",
                     kickoff_at=NOW + timedelta(days=1))
    db.add_all([open_real, closed_real, inactive])
    db.commit()

    result = seed(db, NOW, random.Random(1))

    assert result["predicted"] == UPCOMING_COUNT + 1
    count = lambda m: db.query(Prediction).filter_by(match_id=m.id).count()  # noqa: E731
    assert count(open_real) == 6 >= MIN_PREDICTIONS_FOR_TRENDS
    assert count(closed_real) == 0 and count(inactive) == 0
    demo_open = [m for m in open_matches(db) if m.competition.name == "Démo"]
    assert len(demo_open) == UPCOMING_COUNT and all(count(m) == 6 for m in demo_open)

    reset(db)
    assert db.query(Prediction).count() == 0
    assert db.query(Match).count() == 3  # les matchs réels restent
