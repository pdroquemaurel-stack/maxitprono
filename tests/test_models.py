from datetime import UTC, datetime, timedelta, timezone

import pytest

from app.models import Competition, Match, MatchStatus


def make_match(db, kickoff_at):
    competition = Competition(api_id=2, name="UEFA Champions League", season=2026)
    match = Match(api_id=1001, competition=competition, home_team="A", away_team="B",
                  kickoff_at=kickoff_at)
    db.add(match)
    db.commit()
    db.expire_all()  # force la relecture depuis la base
    return match


def test_kickoff_is_stored_and_read_back_in_utc(db):
    douala_time = timezone(timedelta(hours=1))
    match = make_match(db, datetime(2026, 11, 10, 20, 0, tzinfo=douala_time))
    assert match.kickoff_at == datetime(2026, 11, 10, 19, 0, tzinfo=UTC)
    assert match.kickoff_at.tzinfo is not None


def test_naive_kickoff_is_refused(db):
    with pytest.raises(Exception, match="fuseau"):
        make_match(db, datetime(2026, 11, 10, 20, 0))


def test_new_match_defaults(db):
    match = make_match(db, datetime(2026, 11, 10, 20, 0, tzinfo=UTC))
    assert match.status == MatchStatus.SCHEDULED
    assert match.home_score is None
    assert match.competition.is_active is False
