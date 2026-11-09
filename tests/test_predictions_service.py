from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.exc import IntegrityError

from app.models import Competition, Match, Prediction, User
from app.models.match import MatchStatus
from app.services.predictions import parse_score, save_prediction

KICKOFF = datetime(2026, 11, 10, 19, 0, tzinfo=UTC)
BEFORE = KICKOFF - timedelta(hours=2)


@pytest.fixture
def setup(db):
    competition = Competition(provider="api_football", external_id="61", name="Ligue 1", season=2026, is_active=True)
    match = Match(provider="api_football", external_id="1", competition=competition, home_team="A", away_team="B",
                  kickoff_at=KICKOFF)
    user = User(nickname="Paul", nickname_key="paul", pin_hash="x", country_code="CM",
                rules_accepted_at=BEFORE)
    db.add_all([match, user])
    db.commit()
    return user, match


@pytest.mark.parametrize("raw, expected", [("0", 0), ("3", 3), (" 2 ", 2), ("20", 20),
                                           ("21", None), ("-1", None), ("", None),
                                           ("1.5", None), ("a", None), ("２", None)])
def test_parse_score(raw, expected):
    assert parse_score(raw) == expected


def test_save_creates_prediction(db, setup):
    user, match = setup
    assert save_prediction(db, user.id, match.id, "2", "1", BEFORE) is None
    prediction = db.query(Prediction).one()
    assert (prediction.home_score, prediction.away_score) == (2, 1)
    assert prediction.created_at == BEFORE


def test_save_again_updates_the_same_prediction(db, setup):
    user, match = setup
    save_prediction(db, user.id, match.id, "2", "1", BEFORE)
    later = BEFORE + timedelta(minutes=30)
    save_prediction(db, user.id, match.id, "0", "0", later)
    prediction = db.query(Prediction).one()
    assert (prediction.home_score, prediction.away_score) == (0, 0)
    assert prediction.created_at == BEFORE
    assert prediction.updated_at == later


def test_save_refused_after_deadline(db, setup):
    user, match = setup
    save_prediction(db, user.id, match.id, "2", "1", BEFORE)
    error = save_prediction(db, user.id, match.id, "5", "0", KICKOFF - timedelta(minutes=10))
    assert error == "error_prediction_closed"
    assert db.query(Prediction).one().home_score == 2  # pronostic inchangé


def test_save_refused_on_live_match(db, setup):
    user, match = setup
    match.status = MatchStatus.LIVE
    db.commit()
    assert save_prediction(db, user.id, match.id, "1", "1", BEFORE) == "error_prediction_closed"


def test_save_refused_with_invalid_score(db, setup):
    user, match = setup
    assert save_prediction(db, user.id, match.id, "x", "1", BEFORE) == "error_prediction_score"
    assert save_prediction(db, user.id, match.id, "10", "1", BEFORE) == "error_prediction_score"
    assert db.query(Prediction).count() == 0


def test_save_refused_on_unknown_match(db, setup):
    user, _ = setup
    assert save_prediction(db, user.id, 999, "1", "1", BEFORE) == "error_match_not_found"


def test_concurrent_double_submit_becomes_an_update(db, setup, monkeypatch):
    user, match = setup
    import app.services.predictions as service
    original_upsert, calls = service._upsert, []

    def upsert_losing_the_race(*args):
        if not calls:  # 1er essai : l'autre requête a déjà enregistré son pronostic
            calls.append(1)
            db.add(Prediction(user_id=user.id, match_id=match.id, home_score=9, away_score=9))
            db.commit()
            raise IntegrityError("INSERT", {}, Exception("UNIQUE constraint failed"))
        return original_upsert(*args)

    monkeypatch.setattr(service, "_upsert", upsert_losing_the_race)
    assert save_prediction(db, user.id, match.id, "2", "1", BEFORE) is None
    prediction = db.query(Prediction).one()
    assert (prediction.home_score, prediction.away_score) == (2, 1)
