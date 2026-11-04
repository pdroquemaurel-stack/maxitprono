import random
from datetime import UTC, datetime

from app.models import Competition, Match, Prediction, User
from app.models.match import MatchStatus
from app.services.leaderboards import leaderboard
from scripts.seed_demo import UPCOMING_COUNT, finish_open_matches, reset, seed

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

    assert second == {"players": 6, "past": 0, "upcoming": 0, "scored": second["scored"]}
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
