"""KPIs du back-office : calcul semaine par semaine et lectures en base."""
from datetime import UTC, date, datetime, timedelta

from app.models import ApiCallLog, Competition, Match, Prediction, User
from app.services import kpi_store, league_store
from app.services.kpis import WeekRow, last_mondays, weekly_rows

MONDAY = date(2026, 11, 2)
NOW = datetime(2026, 11, 5, 12, 0, tzinfo=UTC)  # jeudi


def at(day: date, hour: int = 12) -> datetime:
    return datetime(day.year, day.month, day.day, hour, tzinfo=UTC)


def test_last_mondays_current_week_first():
    assert last_mondays(date(2026, 11, 5), 3) == [date(2026, 11, 2), date(2026, 10, 26),
                                                  date(2026, 10, 19)]


def test_weekly_rows_counts_each_week():
    previous = MONDAY - timedelta(weeks=1)
    events = [
        (1, at(MONDAY), at(MONDAY)),  # fait cette semaine
        (1, at(MONDAY), at(MONDAY)),
        (2, at(previous), at(MONDAY + timedelta(days=1))),  # fait avant, modifié cette semaine
        (3, at(previous), at(previous)),
    ]
    rows = weekly_rows([MONDAY, previous], signups=[at(MONDAY), at(previous), at(previous)],
                       prediction_events=events, league_creations=[at(MONDAY)])
    assert rows[0] == WeekRow(MONDAY, new_players=1, active_players=2, predictions=2, leagues=1)
    assert rows[1] == WeekRow(previous, new_players=2, active_players=2, predictions=2, leagues=0)
    assert rows[0].predictions_per_active == 1.0


def test_predictions_per_active_rounding_and_empty_week():
    assert WeekRow(MONDAY, 0, 3, 10, 0).predictions_per_active == 3.3
    assert WeekRow(MONDAY, 0, 0, 0, 0).predictions_per_active == 0.0


def test_sunday_evening_belongs_to_its_week():
    sunday_night = datetime(2026, 11, 8, 23, 30, tzinfo=UTC)
    rows = weekly_rows([MONDAY], [sunday_night], [], [])
    assert rows[0].new_players == 1


# --- En base ---

def add_user(db, nickname, created_at=NOW):
    user = User(nickname=nickname, nickname_key=nickname.lower(), pin_hash="x", country_code="CM",
                rules_accepted_at=created_at, created_at=created_at)
    db.add(user)
    db.commit()
    return user


def test_totals_and_weekly_exclude_demo_players(db):
    paul, demo = add_user(db, "Paul"), add_user(db, "demo_Samuel")
    match = Match(competition=Competition(provider="demo", external_id="demo", name="Démo"),
                  home_team="A", away_team="B", kickoff_at=NOW + timedelta(days=1))
    db.add(match)
    db.flush()
    for user in (paul, demo):
        db.add(Prediction(user_id=user.id, match_id=match.id, home_score=1, away_score=0,
                          created_at=NOW, updated_at=NOW))
    league_store.create_league(db, paul, "Bureau Casa", NOW)
    db.add_all([ApiCallLog(provider="football_data", endpoint="competitions", called_at=NOW),
                ApiCallLog(provider="football_data", endpoint="competitions", called_at=NOW,
                           error="HTTP 429"),
                ApiCallLog(provider="football_data", endpoint="old",
                           called_at=NOW - timedelta(days=10))])
    db.commit()

    totals = kpi_store.totals(db, NOW)
    assert (totals.players, totals.demo_players, totals.leagues, totals.predictions) == (1, 1, 1, 1)
    assert (totals.api_calls, totals.api_errors) == (2, 1)
    assert totals.last_api_error.error == "HTTP 429"

    week = kpi_store.weekly(db, NOW.date())[0]
    assert (week.monday, week.new_players, week.active_players, week.predictions,
            week.leagues) == (MONDAY, 1, 1, 1, 1)
    assert len(kpi_store.weekly(db, NOW.date())) == 8
