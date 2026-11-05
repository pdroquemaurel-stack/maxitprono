"""Back-office : correction de score (verrouillée face à la synchro), ajout de match."""
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from app.jobs.import_matches import import_matches
from app.jobs.score_predictions import rescore_corrected_match
from app.models import Competition, Match, Prediction, User
from app.models.match import MatchStatus
from app.services.admin_matches import parse_correction, parse_new_match
from app.services.scoring import ScoringRules
from tests.test_import_matches import FakeProvider, add_competition
from tests.fixture_factory import fixture_item

NOW = datetime(2026, 11, 5, 12, 0, tzinfo=UTC)


# --- Saisies (fonctions pures) ---

@pytest.mark.parametrize("args, expected", [
    (("finished", "2", "1"), ({"status": "finished", "home_score": 2, "away_score": 1}, None)),
    (("finished", "", ""), (None, "error_final_score_required")),
    (("cancelled", "", ""), ({"status": "cancelled", "home_score": None, "away_score": None}, None)),
    (("live", "1", "0"), ({"status": "live", "home_score": 1, "away_score": 0}, None)),
    (("finished", "2", "x"), (None, "error_score_format")),
    (("finished", "2", ""), (None, "error_score_format")),
    (("other", "", ""), (None, "error_status")),
])
def test_parse_correction(args, expected):
    assert parse_correction(*args) == expected


def test_parse_new_match_converts_local_time_to_utc():
    fields, error = parse_new_match(" Coton  Sport ", "Canon", "2026-11-08", "15:30",
                                    ZoneInfo("Africa/Douala"))
    assert error is None
    assert fields == {"home_team": "Coton Sport", "away_team": "Canon",
                      "kickoff_at": datetime(2026, 11, 8, 14, 30, tzinfo=UTC)}


@pytest.mark.parametrize("args, error", [
    (("", "Canon", "2026-11-08", "15:30"), "error_team_name"),
    (("Canon", "canon", "2026-11-08", "15:30"), "error_same_teams"),
    (("A", "B", "08/11/2026", "15:30"), "error_kickoff"),
    (("A", "B", "2026-11-08", "25:00"), "error_kickoff"),
    (("A" * 121, "B", "2026-11-08", "15:30"), "error_team_name"),
])
def test_parse_new_match_errors(args, error):
    assert parse_new_match(*args, ZoneInfo("UTC")) == (None, error)


# --- Verrou face à la synchro ---

def test_sync_keeps_corrected_score_but_updates_other_fields(db):
    competition = add_competition(db, 61, season=2024)
    import_matches(db, FakeProvider({61: [fixture_item(1, status="FT", goals=(1, 1))]}),
                   date(2024, 8, 1), date(2024, 8, 31))
    match = db.query(Match).one()
    match.home_score, match.away_score, match.score_locked = 2, 1, True
    db.commit()

    renamed = fixture_item(1, status="FT", goals=(1, 1), home="Le Havre AC")
    import_matches(db, FakeProvider({61: [renamed]}), date(2024, 8, 1), date(2024, 8, 31))

    assert (match.home_score, match.away_score, match.status) == (2, 1, MatchStatus.FINISHED)
    assert match.home_team == "Le Havre AC"
    assert competition.id == match.competition_id


# --- Recalcul après correction ---

def add_prediction(db, match, home=2, away=1):
    user = User(nickname="Paul", nickname_key="paul", pin_hash="x", country_code="CM",
                rules_accepted_at=NOW)
    db.add(user)
    db.flush()
    prediction = Prediction(user_id=user.id, match_id=match.id, home_score=home, away_score=away)
    db.add(prediction)
    db.commit()
    return prediction


def make_match(db, status, score):
    competition = Competition(provider="demo", external_id="demo", name="Démo", is_active=True)
    match = Match(competition=competition, home_team="A", away_team="B",
                  kickoff_at=NOW - timedelta(hours=3), status=status,
                  home_score=score[0], away_score=score[1])
    db.add(match)
    db.commit()
    return match


def test_correction_to_finished_scores_predictions(db):
    match = make_match(db, MatchStatus.FINISHED, (2, 1))
    prediction = add_prediction(db, match)
    rescore_corrected_match(db, match, ScoringRules(), NOW)
    assert (prediction.points, prediction.is_exact) == (5, True)


def test_correction_back_to_live_clears_points(db):
    match = make_match(db, MatchStatus.FINISHED, (2, 1))
    prediction = add_prediction(db, match)
    rescore_corrected_match(db, match, ScoringRules(), NOW)
    match.status = MatchStatus.LIVE
    db.commit()
    rescore_corrected_match(db, match, ScoringRules(), NOW)
    assert (prediction.points, prediction.is_exact, prediction.scored_at) == (None, False, None)
