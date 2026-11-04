from datetime import UTC, datetime, timedelta

import pytest

from app.jobs.score_predictions import score_finished_matches, score_match
from app.models import Competition, Match, Prediction, User
from app.models.match import MatchStatus
from app.services.scoring import ScoringRules

KICKOFF = datetime(2026, 11, 10, 19, 0, tzinfo=UTC)
NOW = KICKOFF + timedelta(hours=3)
RULES = ScoringRules()


@pytest.fixture
def make_match(db):
    competition = Competition(api_id=61, name="Ligue 1", season=2026, is_active=True)
    user = User(nickname="Paul", nickname_key="paul", pin_hash="x", country_code="CM",
                rules_accepted_at=KICKOFF)
    db.add_all([competition, user])
    db.commit()

    def factory(status, score=(None, None), prediction=(2, 1), kickoff=KICKOFF):
        match = Match(competition=competition, home_team="A", away_team="B", kickoff_at=kickoff,
                      status=status, home_score=score[0], away_score=score[1])
        db.add(match)
        db.flush()
        pred = Prediction(user_id=user.id, match_id=match.id,
                          home_score=prediction[0], away_score=prediction[1])
        db.add(pred)
        db.commit()
        return match, pred

    return factory


def test_finished_match_is_scored(db, make_match):
    _, exact = make_match(MatchStatus.FINISHED, (2, 1), (2, 1))
    _, winner = make_match(MatchStatus.FINISHED, (1, 0), (3, 1))
    _, miss = make_match(MatchStatus.FINISHED, (0, 0), (3, 1))

    assert score_finished_matches(db, RULES, NOW) == 3

    assert (exact.points, exact.is_exact, exact.is_winner) == (5, True, True)
    assert (winner.points, winner.is_exact, winner.is_winner) == (3, False, True)
    assert (miss.points, miss.is_exact, miss.is_winner) == (0, False, False)
    assert exact.scored_at == NOW


def test_unfinished_matches_are_not_scored(db, make_match):
    _, scheduled = make_match(MatchStatus.SCHEDULED)
    _, live = make_match(MatchStatus.LIVE, (1, 0))
    _, postponed = make_match(MatchStatus.POSTPONED)

    assert score_finished_matches(db, RULES, NOW) == 0
    assert scheduled.scored_at is None and live.scored_at is None and postponed.scored_at is None


def test_cancelled_match_cancels_prediction(db, make_match):
    _, pred = make_match(MatchStatus.CANCELLED)

    score_finished_matches(db, RULES, NOW)

    assert pred.points is None
    assert pred.scored_at == NOW


def test_corrected_score_on_recent_match_is_rescored(db, make_match):
    match, pred = make_match(MatchStatus.FINISHED, (2, 1), (2, 1))
    score_finished_matches(db, RULES, NOW)

    match.away_score = 2  # l'API corrige : 2-2
    db.commit()
    score_finished_matches(db, RULES, NOW + timedelta(hours=1))

    assert (pred.points, pred.is_exact, pred.is_winner) == (0, False, False)


def test_old_scored_match_is_left_alone(db, make_match):
    old_kickoff = NOW - timedelta(days=10)
    _, pred = make_match(MatchStatus.FINISHED, (1, 0), (1, 0), kickoff=old_kickoff)
    score_finished_matches(db, RULES, NOW)

    assert score_finished_matches(db, RULES, NOW + timedelta(hours=1)) == 0
    assert pred.scored_at == NOW


def test_score_match_recomputes_one_match(db, make_match):
    match, pred = make_match(MatchStatus.FINISHED, (1, 1), (0, 0))
    assert score_match(db, match, ScoringRules(winner_points=1, exact_bonus=0), NOW) == 1
    assert pred.points == 1
