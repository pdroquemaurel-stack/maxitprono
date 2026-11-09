"""Boutons du back-office : actualiser les matchs à venir et les scores."""
import pytest

from app.db import get_db
from app.main import app as fastapi_app
from app.models import Competition, User
from app.routes.internal import get_provider_factory
from tests.test_league_pages import register
from tests.test_internal_sync import FakeProvider


@pytest.fixture
def provider():
    fake = FakeProvider()
    fastapi_app.dependency_overrides[get_provider_factory] = lambda: (lambda db: fake)
    yield fake
    fastapi_app.dependency_overrides.pop(get_provider_factory, None)


@pytest.fixture
def admin(client):
    """Paul, connecté et admin, avec une compétition active."""
    register(client)
    db = next(fastapi_app.dependency_overrides[get_db]())
    db.query(User).filter_by(nickname="Paul").one().is_admin = True
    db.add(Competition(provider="football_data", external_id="FL1", name="Ligue 1",
                       season=2026, is_active=True))
    db.commit()
    return client


def test_matches_page_shows_sync_buttons(admin):
    page = admin.get("/admin/matches").text
    assert 'action="/admin/matches/sync/fixtures"' in page
    assert 'action="/admin/matches/sync/scores"' in page


def test_sync_fixtures_imports_and_reports_count(admin, provider):
    response = admin.post("/admin/matches/sync/fixtures", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/admin/matches?task=fixtures&synced=1"
    page = admin.get(response.headers["location"]).text
    assert "1 matchs importés" in page and "PSG – Marseille" in page


def test_sync_scores_without_live_match_makes_no_call(admin, provider):
    response = admin.post("/admin/matches/sync/scores")
    assert "0 matchs mis à jour" in response.text
    assert provider.calls == []


def test_sync_error_is_shown(admin, provider):
    provider.fail = True
    page = admin.post("/admin/matches/sync/fixtures").text
    assert "Synchronisation en échec" in page and "HTTP 429 trop d&#39;appels" in page


def test_unknown_task_is_refused(admin, provider):
    assert admin.post("/admin/matches/sync/other").status_code == 422


def test_sync_hidden_from_players(client, provider):
    register(client)
    assert client.post("/admin/matches/sync/fixtures").status_code == 404
    assert provider.calls == []
