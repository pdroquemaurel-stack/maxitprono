from datetime import timedelta

import pytest
from sqlalchemy.orm import Session

from app.db import get_db
from app.main import app
from app.models import Competition, Match, Prediction
from app.models.match import MatchStatus
from app.models.types import utc_now


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
        competition = Competition(api_id=hash(name) % 10000, name=name, is_active=active)
    match = Match(competition=competition, home_team=home, away_team=away, status=status,
                  kickoff_at=utc_now() + timedelta(hours=hours_from_now),
                  home_score=score[0], away_score=score[1])
    db.add(match)
    db.commit()
    return match


def login(client):
    client.post("/register", data={"nickname": "Paul", "pin": "1234", "country_code": "CM",
                                   "rules_accepted": "true"})


def predict(client, match, home="2", away="1", back="/matches"):
    return client.post(f"/matches/{match.id}/prediction",
                       data={"home_score": home, "away_score": away, "back": back},
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
    add_match(db_session, 24 * 8, home="Lointain")
    page = client.get("/matches").text
    assert "Ancien" not in page and "Lointain" not in page


def test_anonymous_visitor_is_invited_to_log_in(client, db_session):
    add_match(db_session, 24)
    assert "Connecte-toi pour pronostiquer" in client.get("/matches").text


def test_submit_prediction_then_update_it(client, db_session):
    match = add_match(db_session, 24)
    login(client)
    response = predict(client, match)
    assert response.status_code == 303
    assert response.headers["location"] == f"/matches?saved={match.id}#m{match.id}"
    page = client.get(response.headers["location"]).text
    assert "Pronostic enregistré" in page
    assert 'value="2"' in page and "Modifier" in page

    predict(client, match, "0", "0")
    assert db_session.query(Prediction).count() == 1
    db_session.expire_all()
    assert db_session.query(Prediction).one().home_score == 0


def test_prediction_refused_after_deadline(client, db_session):
    match = add_match(db_session, 0.1)  # coup d'envoi dans 6 minutes : clôturé
    login(client)
    response = predict(client, match)
    page = client.get(response.headers["location"]).text
    assert "Trop tard" in page
    assert db_session.query(Prediction).count() == 0


def test_closed_match_shows_no_form(client, db_session):
    add_match(db_session, 0.1)
    login(client)
    page = client.get("/matches").text
    assert "Clôturé" in page
    assert "home_score" not in page


def test_invalid_score_shows_error(client, db_session):
    match = add_match(db_session, 24)
    login(client)
    page = client.get(predict(client, match, "abc", "1").headers["location"]).text
    assert "Score invalide" in page


def test_prediction_requires_login(client, db_session):
    match = add_match(db_session, 24)
    response = predict(client, match)
    assert response.status_code == 303
    assert response.headers["location"] == "/login"


def test_back_page_cannot_redirect_elsewhere(client, db_session):
    match = add_match(db_session, 24)
    login(client)
    response = predict(client, match, back="https://evil.example")
    assert response.headers["location"].startswith("/matches?")


def test_error_text_from_url_is_not_displayed(client, db_session):
    match = add_match(db_session, 24)
    login(client)
    page = client.get(f"/matches?error=<script>&match={match.id}").text
    assert "<script>" not in page


def test_home_shows_matches_to_predict(client, db_session):
    first = add_match(db_session, 24, home="Lions")
    add_match(db_session, 48, home="Aigles")
    login(client)
    page = client.get("/").text
    assert "2 match(s) attendent ton pronostic" in page
    predict(client, first, back="/")
    page = client.get("/").text
    assert "1 match(s) attendent ton pronostic" in page


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
    assert "Lions - Étalons" in page
    assert "score final 3-1" in page
