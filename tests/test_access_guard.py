"""Contrôle d'accès (app/auth/guard.py) : un visiteur ne voit que les pages publiques."""
import re

import pytest
from fastapi.routing import APIRoute

from app.auth.guard import is_public
from app.main import app
from app.models import User
from tests.test_league_pages import create_league, logout, register
from tests.test_match_pages import db_session  # noqa: F401

PUBLIC_PAGES = ["/", "/login", "/register", "/rules", "/help", "/privacy", "/legal"]
PRIVATE_PAGES = ["/matches", "/leaderboard", "/results", "/results/1", "/leagues", "/leagues/new",
                 "/leagues/1", "/leagues/1/settings", "/profile", "/profile/edit",
                 "/profile/history", "/players/1", "/avatars/1", "/admin", "/admin/matches"]


def app_get_paths() -> list[str]:
    """Toutes les pages GET de l'application, paramètres remplacés par 1."""
    return [re.sub(r"\{[^}]+\}", "1", route.path) for route in app.routes
            if isinstance(route, APIRoute) and "GET" in route.methods]


def has_tabbar(page: str) -> bool:
    return '<nav class="tabbar"' in page


# --- Visiteur (navigation privée : aucun cookie) ---

@pytest.mark.parametrize("path", PRIVATE_PAGES)
def test_private_page_redirects_visitor_to_login(client, path):
    response = client.get(path, follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == f"/login?next={path}"


def test_every_non_whitelisted_route_is_private(client):
    """Une nouvelle page est privée d'office : rien à ajouter route par route."""
    for path in app_get_paths():
        if is_public(path):
            continue
        response = client.get(path, follow_redirects=False)
        assert response.status_code == 303, path
        assert response.headers["location"].startswith(("/login?next=", "/register?next=")), path


def test_page_query_is_kept_in_next(client):
    response = client.get("/leaderboard?tab=week", follow_redirects=False)
    assert response.headers["location"] == "/login?next=/leaderboard%3Ftab%3Dweek"


@pytest.mark.parametrize("path", PUBLIC_PAGES)
def test_public_page_shows_without_tabbar(client, path):
    response = client.get(path)
    assert response.status_code == 200
    assert not has_tabbar(response.text)


@pytest.mark.parametrize("path", ["/login", "/register"])
def test_login_pages_have_simple_header(client, path):
    page = client.get(path).text
    assert '<header class="guest-header">' in page and '<a class="p-logo" href="/">' in page
    assert f'href="/language/en?next={path}"' in page


def test_guest_home_links_only_to_public_pages(client):
    links = re.findall(r'href="(/[^"]*)"', client.get("/").text)
    assert links  # l'accueil a bien des liens
    for link in links:
        assert is_public(link.split("?")[0]), link


def test_technical_routes_stay_public(client):
    assert client.get("/health").json() == {"status": "ok"}
    assert client.get("/static/css/style.css").status_code == 200
    assert client.get("/sw.js").status_code == 200
    assert client.get("/offline").status_code == 200


def test_language_switch_returns_to_the_page(client):
    response = client.get("/language/en?next=/rules", follow_redirects=False)
    assert response.headers["location"] == "/rules"
    assert "lang=en" in response.headers["set-cookie"]


def test_api_docs_are_disabled(client):
    for path in ("/docs", "/redoc", "/openapi.json"):
        assert client.get(path, follow_redirects=False).status_code != 200


def test_api_call_without_login_gets_401_json(client):
    response = client.post("/matches/1/prediction", data={"home": "1", "away": "0"},
                           headers={"Accept": "application/json"}, follow_redirects=False)
    assert response.status_code == 401
    assert response.json() == {"detail": "login_required"}


def test_form_post_without_login_goes_to_login(client):
    response = client.post("/leagues", data={"name": "Test"}, follow_redirects=False)
    assert response.headers["location"] == "/login"


def test_internal_sync_keeps_its_own_token(client):
    response = client.post("/internal/sync?task=scores", follow_redirects=False)
    # Refusée par son jeton (SYNC_TOKEN), en JSON : pas de redirection vers /login
    assert response.status_code in (401, 503)
    assert response.headers["content-type"].startswith("application/json")


# --- Connexion et paramètre next ---

def test_login_after_redirect_returns_to_the_page(client):
    register(client)
    logout(client)
    next_url = client.get("/leaderboard", follow_redirects=False).headers["location"]
    assert next_url == "/login?next=/leaderboard"
    page = client.get(next_url).text
    assert 'name="next" value="/leaderboard"' in page
    response = client.post("/login", data={"nickname": "Paul", "pin": "1234",
                                           "next": "/leaderboard"}, follow_redirects=False)
    assert response.headers["location"] == "/leaderboard"


@pytest.mark.parametrize("bad_next", ["https://site-externe.com", "//site-externe.com",
                                      "/\\site-externe.com", "javascript:alert(1)"])
def test_external_next_is_ignored(client, bad_next):
    register(client)
    logout(client)
    response = client.post("/login", data={"nickname": "Paul", "pin": "1234", "next": bad_next},
                           follow_redirects=False)
    assert response.headers["location"] == "/"


def test_invite_link_as_visitor_goes_to_sign_up_then_joins(client, db_session):
    register(client)
    league_id, code = create_league(client)
    logout(client)
    response = client.get(f"/j/{code}", follow_redirects=False)
    assert response.headers["location"] == f"/register?next=/j/{code}"
    page = client.get(response.headers["location"]).text
    assert f'href="/login?next=/j/{code}"' in page  # déjà un compte : lien vers la connexion
    response = register(client, "Awa", next_url=f"/j/{code}")
    assert response.headers["location"] == f"/leagues/{league_id}?joined=1"
    assert "Bienvenue dans la ligue" in client.get(response.headers["location"]).text


# --- Joueur connecté ---

@pytest.mark.parametrize("path", ["/", "/matches", "/leaderboard", "/results", "/leagues",
                                  "/profile", "/rules", "/help", "/privacy", "/legal"])
def test_tabbar_everywhere_when_logged_in(client, path):
    register(client)
    page = client.get(path).text
    assert has_tabbar(page)
    assert '<header class="guest-header">' not in page


def test_tabbar_on_error_page_when_logged_in(client):
    register(client)
    assert has_tabbar(client.get("/nulle-part").text)


@pytest.mark.parametrize("path", ["/login", "/register"])
def test_logged_in_player_is_sent_home_from_login(client, path):
    register(client)
    response = client.get(path, follow_redirects=False)
    assert response.status_code == 303 and response.headers["location"] == "/"


def test_private_pages_are_not_cached(client):
    register(client)
    assert client.get("/profile").headers["cache-control"] == "no-store"
    assert client.get("/").headers["cache-control"] == "no-store"  # accueil joueur


def test_logout_goes_back_to_guest_home(client):
    register(client)
    response = client.post("/logout", follow_redirects=False)
    assert response.headers["location"] == "/"
    page = client.get("/").text
    assert not has_tabbar(page) and "hg-hero" in page
    assert client.get("/profile", follow_redirects=False).status_code == 303


def test_admin_stays_reserved_to_admins(client, db_session):
    register(client)
    assert client.get("/admin").status_code == 403  # joueur ordinaire
    db_session.query(User).filter_by(nickname_key="paul").one().is_admin = True
    db_session.commit()
    assert client.get("/admin").status_code == 200
