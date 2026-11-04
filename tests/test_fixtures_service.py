from datetime import UTC, datetime, timedelta

import pytest

from app.models.match import MatchStatus
from app.services.fixtures import needs_score_update

KICKOFF = datetime(2026, 11, 10, 19, 0, tzinfo=UTC)


def test_live_match_always_needs_update():
    assert needs_score_update(MatchStatus.LIVE, KICKOFF, KICKOFF + timedelta(hours=5))


def test_scheduled_match_needs_update_only_after_kickoff_and_within_window():
    assert not needs_score_update(MatchStatus.SCHEDULED, KICKOFF, KICKOFF - timedelta(minutes=1))
    assert needs_score_update(MatchStatus.SCHEDULED, KICKOFF, KICKOFF + timedelta(minutes=30))
    assert not needs_score_update(MatchStatus.SCHEDULED, KICKOFF, KICKOFF + timedelta(hours=4))


@pytest.mark.parametrize("status", [MatchStatus.FINISHED, MatchStatus.POSTPONED, MatchStatus.CANCELLED])
def test_closed_matches_do_not_need_update(status):
    assert not needs_score_update(status, KICKOFF, KICKOFF + timedelta(minutes=30))

