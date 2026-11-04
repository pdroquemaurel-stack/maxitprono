from datetime import UTC, datetime

from app.models import Competition, Match, Prediction, User
from scripts.reset_football_data import competitions_to_delete, count_data, delete_competitions

NOW = datetime(2026, 11, 4, 12, 0, tzinfo=UTC)


def add_competition(db, provider, external_id, with_prediction_by=None):
    """Une compétition avec un match importé, un match ajouté à la main et un éventuel prono."""
    competition = Competition(provider=provider, external_id=external_id, name=external_id)
    imported = Match(provider=provider, external_id=f"{external_id}-1", competition=competition,
                     home_team="A", away_team="B", kickoff_at=NOW)
    manual = Match(competition=competition, home_team="C", away_team="D", kickoff_at=NOW)
    db.add_all([competition, imported, manual])
    if with_prediction_by:
        db.flush()
        db.add(Prediction(user_id=with_prediction_by.id, match=imported, home_score=1, away_score=0))
    db.commit()
    return competition


def add_user(db):
    user = User(nickname="Paul", nickname_key="paul", pin_hash="x", country_code="CM",
                rules_accepted_at=NOW)
    db.add(user)
    db.commit()
    return user


def setup_data(db):
    user = add_user(db)
    add_competition(db, "api_football", "61", with_prediction_by=user)
    add_competition(db, "football_data", "FL1", with_prediction_by=user)
    add_competition(db, "demo", "demo", with_prediction_by=user)
    return user


def providers_left(db):
    return sorted(c.provider for c in db.query(Competition))


def test_other_providers_are_selected_but_not_demo(db):
    setup_data(db)
    selected = competitions_to_delete(db, "football_data")
    assert [c.provider for c in selected] == ["api_football"]


def test_demo_is_selected_on_request(db):
    setup_data(db)
    selected = competitions_to_delete(db, "football_data", include_demo=True)
    assert [c.provider for c in selected] == ["api_football", "demo"]


def test_count_data_includes_manual_matches_and_predictions(db):
    setup_data(db)
    counts = count_data(db, competitions_to_delete(db, "football_data"))
    assert counts == {"competitions": 1, "matches": 2, "predictions": 1}


def test_counting_changes_nothing(db):
    setup_data(db)
    count_data(db, competitions_to_delete(db, "football_data"))
    assert (db.query(Competition).count(), db.query(Match).count(),
            db.query(Prediction).count()) == (3, 6, 3)


def test_delete_keeps_active_provider_demo_and_players(db):
    setup_data(db)
    delete_competitions(db, competitions_to_delete(db, "football_data"))

    assert providers_left(db) == ["demo", "football_data"]
    assert db.query(Match).count() == 4
    assert db.query(Prediction).count() == 2
    assert db.query(User).count() == 1


def test_delete_with_nothing_selected_is_harmless(db):
    setup_data(db)
    delete_competitions(db, [])
    assert db.query(Competition).count() == 3
