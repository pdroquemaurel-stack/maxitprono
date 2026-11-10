"""Back-office : pages compétitions et matchs."""
import pytest

from app.db import get_db
from app.main import app
from app.models import Competition, Match, Prediction, User
from app.models.match import MatchStatus
from app.routes import admin as admin_routes
from app.providers.base import ProviderError
from tests.test_admin_pages import admin  # noqa: F401
from tests.test_league_pages import register
from tests.test_match_pages import add_match


@pytest.fixture
def db(client):
    session = next(app.dependency_overrides[get_db]())
    yield session
    session.close()


@pytest.mark.parametrize("path", ["/admin/competitions", "/admin/matches", "/admin/matches/new",
                                  "/admin/matches/1"])
def test_new_pages_hidden_from_players(client, path):
    register(client)
    assert client.get(path).status_code == 403


def test_toggle_competition(admin, db):
    competition = Competition(provider="football_data", external_id="FL1", name="Ligue 1",
                              country="France")
    db.add(competition)
    db.commit()
    page = admin.get("/admin/competitions").text
    assert "Ligue 1" in page and "Inactive" in page
    admin.post(f"/admin/competitions/{competition.id}/toggle")
    db.refresh(competition)
    assert competition.is_active is True
    assert "Active" in admin.get("/admin/competitions").text


def test_refresh_competitions_shows_provider_error(admin, monkeypatch):
    def failing(db):
        raise ProviderError("FOOTBALL_DATA_API_KEY manquante")

    monkeypatch.setattr(admin_routes, "make_provider", failing)
    response = admin.post("/admin/competitions/refresh")
    assert response.status_code == 502 and "manquante" in response.text


def test_correct_match_locks_it_and_scores_predictions(admin, db):
    match = add_match(db, -3, status=MatchStatus.LIVE, score=(1, 0))
    match.minute = 54
    paul = db.query(User).filter_by(nickname="Paul").one()
    db.add(Prediction(user_id=paul.id, match_id=match.id, home_score=2, away_score=1))
    db.commit()

    assert "Lions – Étalons" in admin.get("/admin/matches").text
    response = admin.post(f"/admin/matches/{match.id}",
                          data={"status": "finished", "home_score": "2", "away_score": "1"},
                          follow_redirects=False)
    assert response.headers["location"] == "/admin/matches?notice=admin_match_corrected"

    db.expire_all()
    match = db.get(Match, match.id)
    assert (match.status, match.home_score, match.away_score, match.score_locked) == (
        MatchStatus.FINISHED, 2, 1, True)
    assert match.minute is None  # plus de minute après correction
    assert db.query(Prediction).one().points == 5
    assert "corrigé à la main" in admin.get(f"/admin/matches/{match.id}").text


def test_bad_correction_keeps_input(admin, db):
    match = add_match(db, -3, status=MatchStatus.LIVE)
    response = admin.post(f"/admin/matches/{match.id}",
                          data={"status": "finished", "home_score": "", "away_score": ""})
    assert response.status_code == 400 and "doit avoir un score" in response.text


def test_unlock_match(admin, db):
    match = add_match(db, -3, status=MatchStatus.FINISHED, score=(1, 0))
    match.score_locked = True
    db.commit()
    admin.post(f"/admin/matches/{match.id}/unlock")
    db.refresh(match)
    assert match.score_locked is False


def test_add_match_by_hand(admin, db):
    add_match(db, 24, name="Elite One")  # crée la compétition active
    competition = db.query(Competition).filter_by(name="Elite One").one()
    admin.cookies.set("tz", "Africa/Douala")
    response = admin.post("/admin/matches/new", data={
        "competition_id": str(competition.id), "home_team": "Coton Sport", "away_team": "Canon",
        "day": "2030-01-10", "hour": "15:30"}, follow_redirects=False)
    assert response.headers["location"] == "/admin/matches?notice=admin_match_added"
    match = db.query(Match).filter_by(home_team="Coton Sport").one()
    assert match.provider is None and match.external_id is None
    assert match.kickoff_at.hour == 14  # 15:30 à Douala = 14:30 UTC
    assert match.status == MatchStatus.SCHEDULED


def test_add_match_errors(admin, db):
    response = admin.post("/admin/matches/new", data={"competition_id": "999", "home_team": "A",
                                                      "away_team": "B", "day": "2030-01-10",
                                                      "hour": "15:30"})
    assert response.status_code == 400 and "Choisis une compétition" in response.text


def test_unknown_match_is_404(admin):
    assert admin.get("/admin/matches/999").status_code == 404
