"""Choix de la langue : cookie du joueur, sinon langue du téléphone, sinon français."""
import pytest

from app.i18n import current_language, pick_language, set_language, translate
from tests.test_league_pages import create_league, register
from tests.test_match_pages import add_match, db_session  # noqa: F401


@pytest.mark.parametrize("cookie, header, expected", [
    ("en", "fr-FR,fr;q=0.9", "en"),  # le choix du joueur l'emporte
    ("fr", "en-US,en;q=0.9", "fr"),
    (None, "en-US,en;q=0.9,fr;q=0.8", "en"),
    (None, "de-DE,de;q=0.9,en;q=0.5", "en"),  # première langue connue
    (None, "de-DE,de;q=0.9", "fr"),
    (None, None, "fr"),
    ("xx", "en", "en"),  # cookie inconnu ignoré
    (None, "EN", "en"),
])
def test_pick_language(cookie, header, expected):
    assert pick_language(cookie, header) == expected


def test_translate_follows_current_language():
    set_language("en")
    try:
        assert current_language() == "en"
        assert translate("home_title") == "Home"
    finally:
        set_language("fr")
    assert translate("home_title") == "Accueil"


def test_unknown_language_falls_back_to_default():
    set_language("xx")
    assert current_language() == "fr"


def test_phone_language_is_used_without_cookie(client):
    page = client.get("/", headers={"Accept-Language": "en-GB,en;q=0.9"}).text
    assert '<html lang="en">' in page and "English" in page
    assert '<html lang="fr">' in client.get("/").text  # requête suivante : retour au défaut


def test_language_link_sets_cookie_and_returns_to_page(client):
    response = client.get("/language/en?next=/rules", follow_redirects=False)
    assert response.headers["location"] == "/rules"
    assert response.cookies.get("lang") == "en"
    page = client.get("/rules", headers={"Accept-Language": "fr"}).text
    assert '<html lang="en">' in page


def test_language_link_refuses_other_sites_and_unknown_languages(client):
    response = client.get("/language/de?next=https://evil.example", follow_redirects=False)
    assert response.headers["location"] == "/"
    assert "lang" not in response.cookies


def test_register_page_in_english_with_country_names(client):
    client.cookies.set("lang", "en")
    page = client.get("/register").text
    assert "Cameroon" in page and "Cameroun" not in page
    assert 'href="/language/fr?next=/register"' in page


def test_dates_in_english(client, db_session):
    add_match(db_session, 30)
    client.cookies.set("lang", "en")
    page = client.get("/matches").text
    english = ("Today", "Tomorrow", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday",
               "Saturday", "Sunday")
    french = ("Aujourd'hui", "Demain", "lundi", "mardi", "mercredi", "jeudi", "vendredi",
              "samedi", "dimanche")
    assert any(f'day-title">{word}' in page for word in english)
    assert not any(f'day-title">{word}' in page for word in french)


def test_whatsapp_text_in_player_language(client):
    register(client)
    client.cookies.set("lang", "en")
    league_id, _ = create_league(client)
    page = client.get(f"/leagues/{league_id}").text
    assert "Join%20my%20league" in page
    assert "Invite friends on WhatsApp" in page
