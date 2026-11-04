from datetime import UTC, datetime, timedelta

import pytest

from app.models.match import MatchStatus
from app.services.deadlines import is_prediction_open, prediction_deadline

KICKOFF = datetime(2026, 11, 10, 19, 0, tzinfo=UTC)


def test_deadline_is_ten_minutes_before_kickoff():
    assert prediction_deadline(KICKOFF) == datetime(2026, 11, 10, 18, 50, tzinfo=UTC)


def test_open_until_one_second_before_deadline():
    now = KICKOFF - timedelta(minutes=10, seconds=1)
    assert is_prediction_open(MatchStatus.SCHEDULED, KICKOFF, now)


def test_closed_exactly_at_deadline_and_after():
    assert not is_prediction_open(MatchStatus.SCHEDULED, KICKOFF, KICKOFF - timedelta(minutes=10))
    assert not is_prediction_open(MatchStatus.SCHEDULED, KICKOFF, KICKOFF)


@pytest.mark.parametrize("status", [MatchStatus.LIVE, MatchStatus.FINISHED, MatchStatus.CANCELLED])
def test_closed_when_match_started_finished_or_cancelled(status):
    # même si l'heure prévue n'est pas encore passée (ex. coup d'envoi avancé)
    assert not is_prediction_open(status, KICKOFF, KICKOFF - timedelta(days=1))


def test_postponed_match_reopens_with_its_new_date():
    old_kickoff_passed = KICKOFF + timedelta(hours=1)
    assert not is_prediction_open(MatchStatus.POSTPONED, KICKOFF, old_kickoff_passed)
    new_kickoff = KICKOFF + timedelta(days=7)
    assert is_prediction_open(MatchStatus.POSTPONED, new_kickoff, old_kickoff_passed)
