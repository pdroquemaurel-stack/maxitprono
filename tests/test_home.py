from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_home_page_shows_app_name():
    response = client.get("/")
    assert response.status_code == 200
    assert "MaxitProno" in response.text
    assert "Bientôt" in response.text  # français par défaut


def test_health_returns_ok():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_static_css_is_served():
    assert client.get("/static/css/style.css").status_code == 200
