"""Réglages du jeu : saisie, enregistrement, recalcul complet, effets sur le jeu."""
from datetime import UTC, datetime

import pytest
from sqlalchemy.orm import sessionmaker

from app.jobs.score_predictions import rescore_all
from app.models import Competition, Match, Prediction, User
from app.models.match import MatchStatus
from app.services import league_store
from app.services.game_settings import Settings, parse_settings
from app.services.scoring import ScoringRules
from app.services.settings_store import (current_rules, get_settings, league_max_members,
                                         prediction_days_ahead, save_settings)
from scripts import make_admin
from scripts.make_admin import set_admin

NOW = datetime(2026, 11, 5, 12, 0, tzinfo=UTC)


@pytest.mark.parametrize("values, expected", [
    (("3", "2", "100", "14"), (Settings(3, 2, 100, 14), None)),
    ((" 5 ", "0", "2", " 1 "), (Settings(5, 0, 2, 1), None)),
    (("3", "2", "100", "30"), (Settings(3, 2, 100, 30), None)),
    (("21", "2", "100", "14"), (None, "error_points")),
    (("3", "-1", "100", "14"), (None, "error_points")),
    (("3", "x", "100", "14"), (None, "error_points")),
    (("3", "2", "1", "14"), (None, "error_league_size")),
    (("3", "2", "1001", "14"), (None, "error_league_size")),
    (("3", "2", "100", "0"), (None, "error_prediction_days")),
    (("3", "2", "100", "31"), (None, "error_prediction_days")),
    (("3", "2", "100", ""), (None, "error_prediction_days")),
])
def test_parse_settings(values, expected):
    assert parse_settings(*values) == expected


def test_defaults_until_admin_saves(db):
    assert get_settings(db) == Settings(3, 2, 100, 14)
    assert current_rules(db) == ScoringRules(3, 2)


def test_days_setting_is_saved_without_rescoring(db):
    prediction = add_scored_prediction(db, add_user(db))
    assert save_settings(db, Settings(prediction_days_ahead=21), NOW) == 0
    assert prediction_days_ahead(db) == 21
    assert prediction.points == 5


def add_user(db, nickname="Paul"):
    user = User(nickname=nickname, nickname_key=nickname.lower(), pin_hash="x", country_code="CM",
                rules_accepted_at=NOW)
    db.add(user)
    db.commit()
    return user


def add_scored_prediction(db, user):
    competition = Competition(provider="demo", external_id="demo", name="Démo")
    match = Match(competition=competition, home_team="A", away_team="B", kickoff_at=NOW,
                  status=MatchStatus.FINISHED, home_score=2, away_score=1)
    prediction = Prediction(user_id=user.id, match=match, home_score=2, away_score=1,
                            points=5, is_exact=True, is_winner=True)
    db.add(prediction)
    db.commit()
    return prediction


def test_changing_scale_rescores_every_prediction(db):
    prediction = add_scored_prediction(db, add_user(db))
    assert save_settings(db, Settings(4, 3, 100), NOW) == 1
    db.refresh(prediction)
    assert prediction.points == 7
    assert current_rules(db) == ScoringRules(4, 3)


def test_changing_only_league_size_rescores_nothing(db):
    prediction = add_scored_prediction(db, add_user(db))
    assert save_settings(db, Settings(3, 2, 10), NOW) == 0
    assert league_max_members(db) == 10
    assert prediction.points == 5


def test_rescore_all_includes_old_matches_and_cancelled(db):
    prediction = add_scored_prediction(db, add_user(db))
    prediction.match.status = MatchStatus.CANCELLED
    db.commit()
    assert rescore_all(db, ScoringRules(10, 10), NOW) == 1
    assert prediction.points is None


def test_league_size_from_settings(db):
    paul, awa, kevin = add_user(db, "Paul"), add_user(db, "Awa"), add_user(db, "Kevin")
    league = league_store.create_league(db, paul, "Bureau Casa", NOW).league
    save_settings(db, Settings(3, 2, 2), NOW)
    assert league_store.join_league(db, league, awa, NOW).error is None
    assert league_store.join_league(db, league, kevin, NOW).error == "error_league_full"


def test_make_admin(db):
    paul = add_user(db)
    assert set_admin(db, "PAUL", True).is_admin is True
    assert set_admin(db, "paul", False).is_admin is False
    assert set_admin(db, "inconnu", True) is None
    assert paul.is_admin is False


def test_make_admin_command_prints_result(db, monkeypatch, capsys):
    # La commande affiche le résultat sans planter (le joueur est lu avant la fin de la session)
    add_user(db)
    sessions = sessionmaker(bind=db.get_bind())
    monkeypatch.setattr(make_admin, "SessionLocal", sessions)
    monkeypatch.setattr("sys.argv", ["make_admin", "paul"])
    make_admin.main()
    monkeypatch.setattr("sys.argv", ["make_admin", "inconnu", "--off"])
    make_admin.main()
    assert capsys.readouterr().out.splitlines()[-2:] == ["Paul : admin", "Joueur inconnu : inconnu"]
