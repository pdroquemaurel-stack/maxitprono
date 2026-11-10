"""Filtres de la page Pronos et pastille d'état (fonctions pures)."""
from datetime import UTC, date, datetime, timedelta

from app.i18n import format_day_title
from app.models.match import MatchStatus
from app.services.match_filters import (competition_code, competition_keys, is_mine, is_todo,
                                        match_state, matches_status, parse_status)

NOW = datetime(2026, 11, 10, 12, 0, tzinfo=UTC)


def test_competition_code_from_provider_id_then_name_then_initials():
    assert competition_code("FL1", "Ligue 1") == "L1"
    assert competition_code("CL", "UEFA Champions League") == "CL"
    assert competition_code("61", "Ligue 1") == "L1"  # API-Football : identifiant numérique
    assert competition_code("6", "Africa Cup of Nations") == "ACO"
    assert competition_code("12", "Elite One") == "EO"
    assert competition_code("x", "Démo") == "DÉM"


def test_competition_keys_are_lowercase_and_unique():
    assert competition_keys([(1, "L1"), (2, "PL")]) == {1: "l1", 2: "pl"}
    assert competition_keys([(1, "L1"), (7, "L1")]) == {1: "l11", 7: "l17"}
    assert competition_keys([(3, "DÉM")]) == {3: "dem"}


def test_unknown_status_falls_back_to_todo():
    assert parse_status(None) == "todo"
    assert parse_status("nimporte") == "todo"
    assert parse_status("mine") == "mine"


def test_todo_and_mine():
    assert is_todo(is_open=True, has_prediction=False)
    assert not is_todo(is_open=True, has_prediction=True)
    assert not is_todo(is_open=False, has_prediction=False)
    assert is_mine(MatchStatus.SCHEDULED, has_prediction=True)
    assert is_mine(MatchStatus.LIVE, has_prediction=True)  # en cours : reste dans « Mes pronos »
    assert not is_mine(MatchStatus.FINISHED, has_prediction=True)
    assert not is_mine(MatchStatus.SCHEDULED, has_prediction=False)


def test_matches_status():
    assert matches_status("todo", todo=True, mine=False)
    assert not matches_status("todo", todo=False, mine=True)
    assert matches_status("mine", todo=False, mine=True)
    assert matches_status("all", todo=False, mine=False)


def state(status=MatchStatus.SCHEDULED, hours=48, is_open=True, predicted=False):
    return match_state(status, NOW + timedelta(hours=hours), NOW, is_open, predicted)


def test_match_state():
    assert state() == "todo"
    assert state(hours=5) == "closing"  # moins de 24 h
    assert state(predicted=True, hours=5) == "saved"
    assert state(status=MatchStatus.LIVE, hours=-1, is_open=False) == "live"
    assert state(status=MatchStatus.FINISHED, hours=-3, is_open=False) == "finished"
    assert state(status=MatchStatus.CANCELLED, is_open=False) == "cancelled"
    assert state(status=MatchStatus.POSTPONED) == "postponed"
    assert state(hours=0.1, is_open=False) == "closed"  # dans les 10 min avant le coup d'envoi


def test_day_title():
    today = date(2026, 11, 10)  # un mardi
    assert format_day_title(today, today, "fr") == "Aujourd'hui · mar. 10 nov."
    assert format_day_title(date(2026, 11, 11), today, "fr") == "Demain · mer. 11 nov."
    assert format_day_title(date(2026, 11, 14), today, "fr") == "Sam. 14 nov."
    assert format_day_title(date(2026, 11, 14), today, "en") == "Sat 14 Nov"
    assert format_day_title(today, today, "en") == "Today · Tue 10 Nov"
