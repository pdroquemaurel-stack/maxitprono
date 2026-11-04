import dataclasses
from datetime import timedelta

import pytest

import app.config
from app.main import app as fastapi_app
from app.models.types import utc_now
from app.providers.base import ProviderError
from app.routes.internal import get_provider_factory

TOKEN = "s3cret"
AUTH = {"Authorization": f"Bearer {TOKEN}"}


class FakeProvider:
    name = "football_data"

    def __init__(self, fail=False):
        self.fail = fail
        self.calls = []

    def get_matches(self, competition_id, season, date_from, date_to):
        self.calls.append((competition_id, date_from, date_to))
        if self.fail:
            raise ProviderError("HTTP 429 trop d'appels")
        return [{"provider": "football_data", "external_id": "1", "season": 2026,
                 "kickoff_at": utc_now() + timedelta(days=2), "status": "scheduled",
                 "home_team": "PSG", "away_team": "Marseille", "home_logo_url": "",
                 "away_logo_url": "", "home_score": None, "away_score": None}]


@pytest.fixture
def provider(monkeypatch):
    monkeypatch.setattr(app.config, "settings", dataclasses.replace(
        app.config.settings, sync_token=TOKEN, data_provider="football_data"))
    fake = FakeProvider()
    fastapi_app.dependency_overrides[get_provider_factory] = lambda: (lambda db: fake)
    yield fake
    fastapi_app.dependency_overrides.pop(get_provider_factory, None)


def add_active_competition(client):
    """Compétition active du fournisseur, via la session de test de l'app."""
    from app.db import get_db
    from app.models import Competition
    db = next(fastapi_app.dependency_overrides[get_db]())
    db.add(Competition(provider="football_data", external_id="FL1", name="Ligue 1",
                       season=2026, is_active=True))
    db.commit()


def test_missing_token_is_refused(client, provider):
    response = client.post("/internal/sync?task=scores")
    assert response.status_code == 401
    assert provider.calls == []


def test_wrong_token_is_refused(client, provider):
    response = client.post("/internal/sync?task=scores", headers={"Authorization": "Bearer nope"})
    assert response.status_code == 401


def test_route_is_disabled_without_sync_token(client, provider, monkeypatch):
    monkeypatch.setattr(app.config, "settings",
                        dataclasses.replace(app.config.settings, sync_token=""))
    response = client.post("/internal/sync?task=scores", headers={"Authorization": "Bearer "})
    assert response.status_code == 503


def test_unknown_task_is_refused(client, provider):
    assert client.post("/internal/sync?task=other", headers=AUTH).status_code == 422


def test_get_is_not_allowed(client, provider):
    assert client.get("/internal/sync?task=scores", headers=AUTH).status_code == 405


def test_fixtures_imports_matches(client, provider):
    add_active_competition(client)
    response = client.post("/internal/sync?task=fixtures", headers=AUTH)
    assert response.status_code == 200
    assert response.json() == {"task": "fixtures", "provider": "football_data",
                               "matches": 1, "predictions_scored": 0}
    assert [call[0] for call in provider.calls] == ["FL1"]


def test_scores_makes_no_call_without_match_in_progress(client, provider):
    add_active_competition(client)
    response = client.post("/internal/sync?task=scores", headers=AUTH)
    assert response.status_code == 200
    assert response.json()["matches"] == 0
    assert provider.calls == []


def test_provider_error_returns_502_with_message(client, provider):
    add_active_competition(client)
    provider.fail = True
    response = client.post("/internal/sync?task=fixtures", headers=AUTH)
    assert response.status_code == 502
    assert response.json()["error"] == "HTTP 429 trop d'appels"
    assert response.json()["predictions_scored"] == 0


def test_missing_provider_key_returns_502(client, provider):
    def failing_factory(db):
        raise ProviderError("FOOTBALL_DATA_API_KEY manquante")

    fastapi_app.dependency_overrides[get_provider_factory] = lambda: failing_factory
    response = client.post("/internal/sync?task=scores", headers=AUTH)
    assert response.status_code == 502
    assert "manquante" in response.json()["error"]
