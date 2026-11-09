"""Back-office : accès réservé aux admins, page des réglages."""
import pytest

from app.db import get_db
from app.main import app
from app.models import User
from tests.test_league_pages import create_league, logout, register

ADMIN_PAGES = ["/admin", "/admin/settings"]


@pytest.fixture
def admin(client):
    """Paul, connecté et admin."""
    register(client)
    db = next(app.dependency_overrides[get_db]())
    db.query(User).filter_by(nickname="Paul").one().is_admin = True
    db.commit()
    return client


@pytest.mark.parametrize("path", ADMIN_PAGES)
def test_admin_pages_hidden_from_players(client, path):
    register(client)
    assert client.get(path).status_code == 404


@pytest.mark.parametrize("path", ADMIN_PAGES)
def test_admin_pages_need_login(client, path):
    response = client.get(path, follow_redirects=False)
    assert response.headers["location"].startswith("/login?next=/admin")


def test_settings_post_hidden_from_players(client):
    register(client)
    response = client.post("/admin/settings", data={"winner_points": "9", "exact_bonus": "9",
                                                    "league_max_members": "9"})
    assert response.status_code == 404


def test_profile_shows_admin_link_to_admins_only(admin):
    # Le lien est dans « Modifier mon profil » (bouton Modifier et engrenage du profil)
    assert 'href="/admin"' in admin.get("/profile/edit").text
    logout(admin)
    register(admin, "Awa")
    assert 'href="/admin"' not in admin.get("/profile/edit").text
    assert 'href="/admin"' not in admin.get("/profile").text


def test_settings_page_shows_current_values(admin):
    page = admin.get("/admin/settings").text
    assert 'value="3"' in page and 'value="2"' in page and 'value="100"' in page
    assert 'value="14"' in page


def test_save_settings_updates_rules_page_and_league_count(admin):
    league_id, _ = create_league(admin)
    response = admin.post("/admin/settings", data={"winner_points": "4", "exact_bonus": "1",
                                                   "league_max_members": "50",
                                                   "prediction_days_ahead": "21"},
                          follow_redirects=False)
    assert response.headers["location"] == "/admin/settings?saved=1"
    assert "Réglages enregistrés" in admin.get("/admin/settings?saved=1").text
    assert "4 points" in admin.get("/rules").text and "1 points de bonus" in admin.get("/rules").text
    assert "1 / 50 membres" in admin.get(f"/leagues/{league_id}").text
    assert 'value="21"' in admin.get("/admin/settings").text


def test_bad_days_setting_shows_error(admin):
    response = admin.post("/admin/settings", data={"winner_points": "3", "exact_bonus": "2",
                                                   "league_max_members": "100",
                                                   "prediction_days_ahead": "45"})
    assert response.status_code == 400
    assert "entre 1 et 30" in response.text and 'value="45"' in response.text


def test_bad_settings_keep_input_and_show_error(admin):
    response = admin.post("/admin/settings", data={"winner_points": "99", "exact_bonus": "2",
                                                   "league_max_members": "100"})
    assert response.status_code == 400
    assert "entre 0 et 20" in response.text and 'value="99"' in response.text


def test_rules_page_shows_default_scale(client):
    page = client.get("/rules").text
    assert "3 points" in page and "2 points de bonus" in page


def test_admin_home_shows_kpis(admin):
    page = admin.get("/admin").text
    assert "joueurs inscrits" in page and "Semaine par semaine" in page
    assert page.count("<tr>") == 9  # en-tête + 8 semaines
    assert 'href="/admin/competitions"' in page
