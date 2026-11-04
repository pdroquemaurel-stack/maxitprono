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


# --- Délai avant clôture affiché ---

from zoneinfo import ZoneInfo  # noqa: E402

from app.services.deadlines import closing_info  # noqa: E402

PARIS = ZoneInfo("Europe/Paris")  # UTC+1 en novembre


def test_closing_soon_gives_hours_and_minutes():
    now = KICKOFF - timedelta(minutes=10 + 102)  # clôture dans 1 h 42
    info = closing_info(KICKOFF, now, UTC)
    assert (info.kind, info.hours, info.minutes) == ("soon", 1, 42)


def test_closing_in_less_than_a_minute_shows_one_minute():
    info = closing_info(KICKOFF, KICKOFF - timedelta(minutes=10, seconds=20), UTC)
    assert (info.kind, info.hours, info.minutes) == ("soon", 0, 1)


def test_closing_later_today_still_gives_the_duration():
    now = datetime(2026, 11, 10, 8, 0, tzinfo=UTC)  # clôture à 18:50, le même jour
    assert closing_info(KICKOFF, now, UTC).hours == 10


def test_closing_tomorrow():
    now = datetime(2026, 11, 9, 9, 0, tzinfo=UTC)
    assert closing_info(KICKOFF, now, UTC).kind == "tomorrow"


def test_closing_within_six_hours_shows_duration_even_tomorrow():
    now = datetime(2026, 11, 10, 20, 0, tzinfo=UTC)  # 4 h 20 avant la clôture
    late_kickoff = datetime(2026, 11, 11, 0, 30, tzinfo=UTC)  # clôture à 00:20, demain
    assert closing_info(late_kickoff, now, UTC).kind == "soon"


def test_closing_later_gives_the_local_day():
    now = datetime(2026, 11, 7, 12, 0, tzinfo=UTC)
    info = closing_info(KICKOFF, now, UTC)
    assert (info.kind, info.day) == ("later", KICKOFF.date())


def test_closing_day_uses_player_timezone():
    # Clôture à 23:30 UTC le 9 = 00:30 le 10 à Paris
    kickoff = datetime(2026, 11, 9, 23, 40, tzinfo=UTC)
    now = datetime(2026, 11, 8, 12, 0, tzinfo=UTC)
    assert closing_info(kickoff, now, UTC).kind == "tomorrow"
    assert closing_info(kickoff, now, PARIS).kind == "later"
