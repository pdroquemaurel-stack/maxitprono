from datetime import timedelta

import pytest
from sqlalchemy.orm import Session

from app.db import get_db
from app.main import app
from app.models import Competition, Match, Prediction
from app.models.match import MatchStatus
from app.models.types import utc_now
from app.services.game_settings import Settings
from app.services.settings_store import save_settings


@pytest.fixture
def db_session(client):
    """Session sur la même base que le client de test."""
    session: Session = next(app.dependency_overrides[get_db]())
    yield session
    session.close()


def add_match(db, hours_from_now, home="Lions", away="Étalons", status=MatchStatus.SCHEDULED,
              active=True, score=(None, None), name="Ligue 1"):
    competition = db.query(Competition).filter_by(name=name).first()
    if competition is None:
        competition = Competition(provider="api_football", external_id=str(hash(name) % 10000), name=name, is_active=active)
    match = Match(competition=competition, home_team=home, away_team=away, status=status,
                  kickoff_at=utc_now() + timedelta(hours=hours_from_now),
                  home_score=score[0], away_score=score[1])
    db.add(match)
    db.commit()
    return match


def login(client):
    client.post("/register", data={"nickname": "Paul", "pin": "1234", "country_code": "CM",
                                   "rules_accepted": "true"})


def predict(client, match, home="2", away="1"):
    """Envoi automatique d'un prono, comme le fait static/js/predictions.js."""
    return client.post(f"/matches/{match.id}/prediction", data={"home": home, "away": away},
                       follow_redirects=False)


def test_matches_page_lists_active_competitions_only(client, db_session):
    add_match(db_session, 24, home="Lions")
    add_match(db_session, 24, home="Cachés", name="Inactive", active=False)
    page = client.get("/matches")
    assert page.status_code == 200
    assert "Lions" in page.text
    assert "Cachés" not in page.text


def test_matches_page_hides_old_and_far_matches(client, db_session):
    add_match(db_session, -5, home="Ancien")
    add_match(db_session, 24 * 13, home="Proche")
    add_match(db_session, 24 * 15, home="Lointain")
    page = client.get("/matches").text
    assert "Proche" in page  # 14 jours par défaut
    assert "Ancien" not in page and "Lointain" not in page


def test_matches_page_follows_admin_days_setting(client, db_session):
    save_settings(db_session, Settings(prediction_days_ahead=3), utc_now())
    add_match(db_session, 24 * 2, home="Bientôt")
    add_match(db_session, 24 * 4, home="Après")
    page = client.get("/matches").text
    assert "Bientôt" in page and "Après" not in page


def test_anonymous_visitor_is_invited_to_log_in(client, db_session):
    add_match(db_session, 24)
    assert "Connecte-toi pour pronostiquer" in client.get("/matches").text


def test_submit_prediction_then_update_it(client, db_session):
    match = add_match(db_session, 24)
    login(client)
    response = predict(client, match)
    assert response.status_code == 200
    assert response.json() == {"saved": True}
    page = client.get("/matches").text
    assert 'value="2"' in page and "Enregistré" in page

    predict(client, match, "0", "0")
    assert db_session.query(Prediction).count() == 1
    db_session.expire_all()
    assert db_session.query(Prediction).one().home_score == 0


def test_score_above_9_is_refused(client, db_session):
    match = add_match(db_session, 24)
    login(client)
    response = predict(client, match, "10", "1")
    assert response.status_code == 400
    assert response.json() == {"saved": False,
                               "error": "Score invalide : un chiffre de 0 à 9 dans chaque case."}
    assert db_session.query(Prediction).count() == 0


def test_prediction_refused_after_deadline(client, db_session):
    match = add_match(db_session, 0.1)  # coup d'envoi dans 6 minutes : clôturé
    login(client)
    response = predict(client, match)
    assert response.status_code == 400
    assert "Trop tard" in response.json()["error"]
    assert db_session.query(Prediction).count() == 0


def test_unknown_match_returns_404(client, db_session):
    login(client)
    response = client.post("/matches/999/prediction", data={"home": "1", "away": "0"})
    assert response.status_code == 404
    assert response.json()["saved"] is False


def test_page_has_autosave_inputs_and_no_save_button(client, db_session):
    match = add_match(db_session, 24)
    login(client)
    page = client.get("/matches").text
    assert f'data-match-id="{match.id}"' in page
    assert 'maxlength="1"' in page and "js/predictions.js" in page
    assert "Enregistrer mes pronos" not in page and 'type="submit"' not in page


def test_error_message_in_english(client, db_session):
    match = add_match(db_session, 24)
    login(client)
    client.cookies.set("lang", "en")
    assert "one digit from 0 to 9" in predict(client, match, "x", "1").json()["error"]


def test_closed_match_shows_no_input(client, db_session):
    match = add_match(db_session, 0.1)
    login(client)
    page = client.get("/matches").text
    assert "Clôturé" in page
    assert f'name="home_{match.id}"' not in page


def test_invalid_score_shows_error(client, db_session):
    match = add_match(db_session, 24)
    login(client)
    assert "Score invalide" in predict(client, match, "abc", "1").json()["error"]


def test_prediction_requires_login(client, db_session):
    match = add_match(db_session, 24)
    response = predict(client, match)
    assert response.status_code == 303
    assert response.headers["location"] == "/login"


def test_saved_prediction_is_colored_and_closing_time_shown(client, db_session):
    add_match(db_session, 24, home="Lions")
    saved = add_match(db_session, 30, home="Aigles")
    login(client)
    predict(client, saved, "1", "1")
    page = client.get("/matches").text
    assert "score-box draw" in page
    assert "Ferme " in page  # le match sans prono affiche sa clôture
    assert "1 à faire" in page


def test_home_shows_matches_to_predict(client, db_session):
    first = add_match(db_session, 24, home="Lions")
    add_match(db_session, 48, home="Aigles")
    login(client)
    page = client.get("/").text
    assert "2 pronos à faire" in page and "Le premier ferme dans" in page
    predict(client, first)
    page = client.get("/").text
    assert "1 prono à faire" in page
    predict(client, add_match(db_session, 72))
    predict(client, db_session.query(Match).filter_by(home_team="Aigles").one())
    page = client.get("/").text
    assert "Tous tes pronos sont prêts" in page and "Lions – Étalons" in page  # prochain match


def test_times_shown_in_player_timezone(client, db_session):
    match = add_match(db_session, 24)
    client.cookies.set("tz", "Asia/Tokyo")  # UTC+9, sans heure d'été
    expected = (match.kickoff_at + timedelta(hours=9)).strftime("%H:%M")
    assert expected in client.get("/matches").text


def test_profile_history_shows_final_score(client, db_session):
    match = add_match(db_session, 24, home="Lions", away="Étalons")
    login(client)
    predict(client, match, "2", "1")
    match.status, match.home_score, match.away_score = MatchStatus.FINISHED, 3, 1
    db_session.commit()
    page = client.get("/profile/history").text
    assert "Lions – Étalons" in page
    assert "score final 3–1" in page
    assert '<span class="win">2</span>' in page
