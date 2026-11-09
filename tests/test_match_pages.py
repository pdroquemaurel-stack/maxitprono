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
    return client.post("/matches/predictions",
                       data={f"home_{match.id}": home, f"away_{match.id}": away},
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
    assert response.status_code == 303
    assert response.headers["location"] == "/matches?saved=1"
    page = client.get(response.headers["location"]).text
    assert "1 prono enregistré" in page
    assert 'value="2"' in page and "Enregistré" in page

    predict(client, match, "0", "0")
    assert db_session.query(Prediction).count() == 1
    db_session.expire_all()
    assert db_session.query(Prediction).one().home_score == 0


def test_save_several_predictions_at_once_and_skip_empty_ones(client, db_session):
    first, second, empty = add_match(db_session, 24), add_match(db_session, 30), add_match(db_session, 36)
    login(client)
    response = client.post("/matches/predictions", follow_redirects=False, data={
        f"home_{first.id}": "2", f"away_{first.id}": "1",
        f"home_{second.id}": "0", f"away_{second.id}": "3",
        f"home_{empty.id}": "", f"away_{empty.id}": "",
    })
    assert response.headers["location"] == "/matches?saved=2"
    assert db_session.query(Prediction).count() == 2


def test_one_bad_match_does_not_block_the_others(client, db_session):
    good, bad = add_match(db_session, 24, home="Bons"), add_match(db_session, 30, home="Mauvais")
    login(client)
    response = client.post("/matches/predictions", data={
        f"home_{good.id}": "1", f"away_{good.id}": "1",
        f"home_{bad.id}": "3", f"away_{bad.id}": "",
    })
    assert response.status_code == 200  # page réaffichée, pas de redirection
    assert "Score invalide" in response.text
    assert "1 prono enregistré" in response.text
    assert 'value="3"' in response.text  # la saisie refusée est conservée
    assert db_session.query(Prediction).one().match_id == good.id


def test_prediction_refused_after_deadline(client, db_session):
    match = add_match(db_session, 0.1)  # coup d'envoi dans 6 minutes : clôturé
    login(client)
    page = predict(client, match).text
    assert "Trop tard" in page
    assert db_session.query(Prediction).count() == 0


def test_closed_match_shows_no_input(client, db_session):
    match = add_match(db_session, 0.1)
    login(client)
    page = client.get("/matches").text
    assert "Clôturé" in page
    assert f'name="home_{match.id}"' not in page


def test_invalid_score_shows_error(client, db_session):
    match = add_match(db_session, 24)
    login(client)
    page = predict(client, match, "abc", "1").text
    assert "Score invalide" in page


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


def test_bad_saved_parameter_is_ignored(client, db_session):
    add_match(db_session, 24)
    assert client.get("/matches?saved=<script>").status_code == 200


def test_home_shows_matches_to_predict(client, db_session):
    first = add_match(db_session, 24, home="Lions")
    add_match(db_session, 48, home="Aigles")
    login(client)
    page = client.get("/").text
    assert "2 matchs sans prono" in page
    assert "Le premier ferme demain" in page or "Le premier ferme dans" in page
    predict(client, first)
    page = client.get("/").text
    assert "1 match sans prono" in page
    predict(client, add_match(db_session, 72))
    predict(client, db_session.query(Match).filter_by(home_team="Aigles").one())
    assert "Tous tes pronos sont faits" in client.get("/").text


def test_times_shown_in_player_timezone(client, db_session):
    match = add_match(db_session, 24)
    client.cookies.set("tz", "Asia/Tokyo")  # UTC+9, sans heure d'été
    expected = (match.kickoff_at + timedelta(hours=9)).strftime("%H:%M")
    assert expected in client.get("/matches").text


def test_profile_shows_history_with_final_score(client, db_session):
    match = add_match(db_session, 24, home="Lions", away="Étalons")
    login(client)
    predict(client, match, "2", "1")
    match.status, match.home_score, match.away_score = MatchStatus.FINISHED, 3, 1
    db_session.commit()
    page = client.get("/profile").text
    assert "Lions – Étalons" in page
    assert "score final 3–1" in page
    assert '<span class="win">2</span>' in page
