def test_home_page_shows_app_name(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "MaxitProno" in response.text
    assert "Jouer gratuitement" in response.text  # français par défaut


def test_health_returns_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_static_files_are_served(client):
    assert client.get("/static/css/style.css").status_code == 200
    assert client.get("/static/js/avatar.js").status_code == 200
