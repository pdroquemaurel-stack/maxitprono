from dataclasses import dataclass
from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

from app.services.timezones import (
    DEFAULT_TIMEZONE,
    group_by_day,
    local_day,
    resolve_timezone,
)


@dataclass(frozen=True)
class FakeCompetition:
    name: str


@dataclass
class FakeMatch:
    kickoff_at: datetime
    competition: FakeCompetition


L1, CL = FakeCompetition("Ligue 1"), FakeCompetition("Champions League")


def test_resolve_timezone():
    assert resolve_timezone("Africa/Ouagadougou") == ZoneInfo("Africa/Ouagadougou")
    assert resolve_timezone(None) == ZoneInfo(DEFAULT_TIMEZONE)
    assert resolve_timezone("Pas/Un_Fuseau") == ZoneInfo(DEFAULT_TIMEZONE)
    assert resolve_timezone("../../etc/passwd") == ZoneInfo(DEFAULT_TIMEZONE)


def test_late_utc_match_is_next_day_in_douala():
    kickoff = datetime(2026, 11, 10, 23, 30, tzinfo=UTC)
    assert local_day(kickoff, ZoneInfo("Africa/Ouagadougou")) == date(2026, 11, 10)  # UTC+0
    assert local_day(kickoff, ZoneInfo("Africa/Douala")) == date(2026, 11, 11)  # UTC+1


def test_group_by_day_in_kickoff_order():
    matches = [
        FakeMatch(datetime(2026, 11, 10, 18, 0, tzinfo=UTC), L1),
        FakeMatch(datetime(2026, 11, 10, 20, 0, tzinfo=UTC), CL),
        FakeMatch(datetime(2026, 11, 10, 23, 30, tzinfo=UTC), L1),  # le 11 à Paris
    ]
    days = group_by_day(matches, ZoneInfo("Europe/Paris"))
    assert [(day, len(items)) for day, items in days] == [(date(2026, 11, 10), 2),
                                                          (date(2026, 11, 11), 1)]


def test_falls_back_to_utc_without_timezone_database(monkeypatch):
    from datetime import UTC

    import app.services.timezones as timezones

    def missing(name):
        raise timezones.ZoneInfoNotFoundError(name)

    monkeypatch.setattr(timezones, "ZoneInfo", missing)
    assert timezones.resolve_timezone("Africa/Douala") == UTC
