"""Calendrier de la page Pronos (fonctions pures)."""
from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

from app.services.match_days import calendar_days, calendar_end, match_day, pick_day

TODAY = date(2026, 11, 11)
DOUALA = ZoneInfo("Africa/Douala")  # UTC+1


def test_calendar_starts_today_with_admin_day_count():
    assert calendar_days(TODAY, 3) == [date(2026, 11, 11), date(2026, 11, 12), date(2026, 11, 13)]
    assert len(calendar_days(TODAY, 14)) == 14


def test_calendar_always_has_today():
    assert calendar_days(TODAY, 0) == [TODAY]


def test_pick_day_from_address_or_today():
    days = calendar_days(TODAY, 5)
    assert pick_day("2026-11-13", days) == date(2026, 11, 13)
    assert pick_day(None, days) == TODAY
    assert pick_day("n'importe quoi", days) == TODAY
    assert pick_day("2026-11-30", days) == TODAY  # hors du calendrier


def test_match_day_is_local_day():
    # 23:30 UTC = 00:30 le lendemain à Douala
    assert match_day(datetime(2026, 11, 12, 23, 30, tzinfo=UTC), DOUALA, TODAY) == date(2026, 11, 13)


def test_match_started_yesterday_counts_today():
    assert match_day(datetime(2026, 11, 10, 22, 0, tzinfo=UTC), DOUALA, TODAY) == TODAY


def test_calendar_end_is_midnight_after_last_day_local_time():
    end = calendar_end(calendar_days(TODAY, 2), DOUALA)
    assert end == datetime(2026, 11, 12, 23, 0, tzinfo=UTC)  # 13/11 00:00 à Douala
