"""Pages d'erreur 404 / 500, page hors connexion et service worker."""
from fastapi.testclient import TestClient

import app.routes.home as home_routes
from app.main import app


def test_unknown_page_shows_error_page_with_retry(client):
    response = client.get("/nulle-part?x=1")
    assert response.status_code == 404
    assert "Page introuvable" in response.text
    assert 'href="/nulle-part?x=1"' in response.text and "Réessayer" in response.text
    assert "Retour à l&#39;accueil" in response.text or "Retour à l'accueil" in response.text


def test_404_from_a_route_uses_the_page_too(client):
    assert "Page introuvable" in client.get("/results/999").text


def test_error_page_in_english(client):
    response = client.get("/nulle-part", headers={"Accept-Language": "en"})
    assert "Page not found" in response.text and "Try again" in response.text


def test_internal_route_errors_stay_json(client):
    response = client.post("/internal/sync?task=scores")
    assert response.headers["content-type"].startswith("application/json")


def test_server_error_shows_error_page(client, monkeypatch):
    def broken(db):
        raise RuntimeError("panne")

    monkeypatch.setattr(home_routes, "current_rules", broken)
    with TestClient(app, raise_server_exceptions=False) as raw_client:
        response = raw_client.get("/rules")
    assert response.status_code == 500
    assert "un problème de notre côté" in response.text and "Réessayer" in response.text


def test_offline_page_in_both_languages(client):
    page = client.get("/offline")
    assert page.status_code == 200 and "Pas de connexion" in page.text
    assert 'location.reload()' in page.text and "tabbar" not in page.text
    assert "No connection" in client.get("/offline", headers={"Accept-Language": "en"}).text


def test_service_worker_served_from_root(client):
    response = client.get("/sw.js")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/javascript")
    assert response.headers["cache-control"] == "no-cache"
    assert '"/offline"' in response.text


def test_pages_register_the_service_worker(client):
    assert 'navigator.serviceWorker.register("/sw.js")' in client.get("/").text
