from datetime import UTC, datetime, timedelta

import pytest

from app.models.match import MatchStatus
from app.services.fixtures import map_fixture_status, needs_score_update, parse_fixture
from tests.fixture_factory import fixture_item

KICKOFF = datetime(2026, 11, 10, 19, 0, tzinfo=UTC)


@pytest.mark.parametrize("code, expected", [
    ("NS", MatchStatus.SCHEDULED), ("TBD", MatchStatus.SCHEDULED),
    ("1H", MatchStatus.LIVE), ("HT", MatchStatus.LIVE), ("P", MatchStatus.LIVE),
    ("FT", MatchStatus.FINISHED), ("AET", MatchStatus.FINISHED), ("PEN", MatchStatus.FINISHED),
    ("PST", MatchStatus.POSTPONED),
    ("CANC", MatchStatus.CANCELLED), ("ABD", MatchStatus.CANCELLED),
    ("XYZ", MatchStatus.SCHEDULED),
])
def test_map_fixture_status(code, expected):
    assert map_fixture_status(code) == expected


def test_parse_fixture_finished_match():
    fields = parse_fixture(fixture_item(status="FT", goals=(1, 4)))
    assert fields["api_id"] == 1001
    assert fields["season"] == 2024
    assert fields["kickoff_at"] == datetime(2024, 8, 16, 19, 0, tzinfo=UTC)
    assert fields["status"] == MatchStatus.FINISHED
    assert (fields["home_team"], fields["away_team"]) == ("Le Havre", "PSG")
    assert (fields["home_score"], fields["away_score"]) == (1, 4)


def test_parse_fixture_keeps_timezone():
    fields = parse_fixture(fixture_item(date="2024-08-16T21:00:00+02:00"))
    assert fields["kickoff_at"] == datetime(2024, 8, 16, 19, 0, tzinfo=UTC)


def test_live_match_always_needs_update():
    assert needs_score_update(MatchStatus.LIVE, KICKOFF, KICKOFF + timedelta(hours=5))


def test_scheduled_match_needs_update_only_after_kickoff_and_within_window():
    assert not needs_score_update(MatchStatus.SCHEDULED, KICKOFF, KICKOFF - timedelta(minutes=1))
    assert needs_score_update(MatchStatus.SCHEDULED, KICKOFF, KICKOFF + timedelta(minutes=30))
    assert not needs_score_update(MatchStatus.SCHEDULED, KICKOFF, KICKOFF + timedelta(hours=4))


@pytest.mark.parametrize("status", [MatchStatus.FINISHED, MatchStatus.POSTPONED, MatchStatus.CANCELLED])
def test_closed_matches_do_not_need_update(status):
    assert not needs_score_update(status, KICKOFF, KICKOFF + timedelta(minutes=30))

