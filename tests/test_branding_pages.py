"""Admin → Personnalisation : accès, enregistrement, nom et couleurs appliqués sur tout le site."""
import re

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models import BrandingChange
from tests.test_admin_pages import admin  # noqa: F401 (fixture : Paul, connecté et admin)
from tests.test_league_pages import create_league, logout, register
from tests.test_match_pages import add_match, db_session  # noqa: F401

DEFAULT_FORM = {"app_name": "MaxitProno", "logo_part1": "Maxit", "logo_part2": "Prono",
                "publisher_name": "Max it", "tagline_fr": "Pronostique les scores. Défie tes amis.",
                "tagline_en": "Predict the scores. Challenge your friends.",
                "color_primary": "#FF7900", "color_dark": "#0B0E13"}
VESTIAIRE = DEFAULT_FORM | {"app_name": "Mon Vestiaire", "logo_part1": "Mon",
                            "logo_part2": "Vestiaire", "publisher_name": "Le Club"}
LOGO = 'Mon <span class="p-logo-pill">Vestiaire</span>'


def save(client, **changes):
    return client.post("/admin/branding", data=DEFAULT_FORM | changes, follow_redirects=False)


def brand_variable(page: str, name: str) -> str:
    """Valeur d'une variable du bloc <style>:root{…}</style> injecté dans <head>."""
    return re.search(r"<style>:root\{[^}]*" + name + r":(#[0-9A-F]{6});", page).group(1)


def title(page: str) -> str:
    return re.search(r"<title>(.*?)</title>", page).group(1)


# --- Accès ---

@pytest.mark.parametrize("method, path", [("get", "/admin/branding"), ("post", "/admin/branding"),
                                          ("post", "/admin/branding/reset")])
def test_branding_forbidden_to_players(client, method, path):
    register(client)
    response = client.get(path) if method == "get" else client.post(path, data=VESTIAIRE)
    assert response.status_code == 403
    assert "Mon Vestiaire" not in client.get("/").text  # rien n'a été enregistré


def test_branding_needs_login(client):
    response = client.get("/admin/branding", follow_redirects=False)
    assert response.headers["location"] == "/login?next=/admin/branding"


def test_admin_home_links_to_branding(admin):
    assert 'href="/admin/branding"' in admin.get("/admin").text


def test_branding_page_shows_defaults_and_preview(admin):
    page = admin.get("/admin/branding").text
    assert 'value="MaxitProno"' in page and 'value="#FF7900"' in page
    assert 'type="color"' in page and "data-brand-preview" in page
    assert "noir, contraste 8.0:1" in page
    assert "Aucune modification pour l&#39;instant." in page


# --- Le nom partout ---

def test_new_name_everywhere_in_french_and_english(admin, db_session):
    add_match(db_session, 5)
    assert save(admin, **VESTIAIRE).headers["location"].startswith("/admin/branding?notice=saved")
    create_league(admin)  # pour que Ligues et l'accueil aient une ligue
    for lang, by in (("fr", "Mon Vestiaire par Le Club"), ("en", "Mon Vestiaire by Le Club")):
        admin.get(f"/language/{lang}")
        for path in ("/", "/matches", "/leagues", "/profile"):
            page = admin.get(path).text
            assert "Mon Vestiaire" in title(page), (lang, path)
            assert "Maxit" not in page, (lang, path)
            assert 'og:site_name" content="Mon Vestiaire"' in page
        assert LOGO in admin.get("/").text and LOGO in admin.get("/profile").text
        # Visiteur (sans cookie de session) : accueil, connexion, pied de page
        guest = TestClient(app)
        guest.get(f"/language/{lang}")
        for path in ("/", "/login"):
            page = guest.get(path).text
            assert "Mon Vestiaire" in title(page) and LOGO in page, (lang, path)
            assert "Maxit" not in page, (lang, path)
        assert by in guest.get("/").text


def test_new_name_in_share_messages(admin):
    save(admin, **VESTIAIRE)
    league_id, _ = create_league(admin)
    page = admin.get(f"/leagues/{league_id}").text
    assert "sur Mon Vestiaire" in page  # message WhatsApp prérempli (data-share-text et wa.me)
    assert "sur%20Mon%20Vestiaire" in page
    assert "sur Mon Vestiaire. Viens me défier" in admin.get("/profile").text


def test_tagline_on_guest_home_and_meta(admin):
    save(admin, tagline_fr="Prends le vestiaire. Chambre tes potes.")
    logout(admin)
    page = admin.get("/").text
    assert "Prends le vestiaire.<br><span>Chambre tes potes.</span>" in page
    assert '<meta name="description" content="Prends le vestiaire. Chambre tes potes.">' in page


# --- Couleurs ---

def test_blue_then_light_yellow_switch_button_text(admin):
    save(admin, color_primary="#1F6FEB")
    page = admin.get("/").text
    assert brand_variable(page, "--color-primary") == "#1F6FEB"
    assert brand_variable(page, "--color-on-primary") == "#FFFFFF"  # texte blanc sur le bleu
    assert '<meta name="theme-color" content="#0B0E13">' in page  # la couleur de fond
    assert '<meta name="color-scheme" content="dark">' in page
    assert 'fill="#1F6FEB"' in admin.get("/icon.svg").text

    save(admin, color_primary="#FFF7B0")
    page = admin.get("/").text
    assert brand_variable(page, "--color-on-primary") == "#000000"  # texte noir sur le jaune
    assert "noir, contraste 19.2:1" in admin.get("/admin/branding").text


def test_dark_color_too_light_is_refused(admin):
    response = save(admin, color_dark="#EEEEEE")
    assert response.status_code == 400
    assert "le texte blanc posé dessus serait illisible" in response.text
    assert brand_variable(admin.get("/").text, "--color-dark") == "#0B0E13"


def test_no_brand_color_left_in_css():
    from app.main import STATIC_DIR
    css = (STATIC_DIR / "css" / "style.css").read_text().upper()
    for color in ("#FF7900", "#FFF3E8", "#FFE7D1", "#7A3900", "#7A3600", "#B34F00", "#FFF1E6"):
        assert color not in css


# --- Rétablir ---

def test_reset_restores_exact_look(admin):
    logout(admin)
    before = {path: admin.get(path).text for path in ("/", "/login")}
    admin.post("/login", data={"nickname": "Paul", "pin": "1234"})
    save(admin, **VESTIAIRE | {"color_primary": "#1F6FEB", "color_dark": "#0B2540"})
    response = admin.post("/admin/branding/reset", follow_redirects=False)
    assert response.headers["location"] == "/admin/branding?notice=reset"
    assert "Valeurs par défaut rétablies." in admin.get(response.headers["location"]).text
    logout(admin)
    assert {path: admin.get(path).text for path in before} == before


# --- Historique ---

def test_history_records_who_what_when(admin, db_session):
    save(admin, app_name="Mon Vestiaire")
    save(admin, app_name="Mon Vestiaire", color_primary="#1F6FEB")
    changes = db_session.query(BrandingChange).order_by(BrandingChange.id).all()
    assert [(c.field, c.old_value, c.new_value) for c in changes] == [
        ("app_name", "MaxitProno", "Mon Vestiaire"), ("color_primary", "#FF7900", "#1F6FEB")]
    page = admin.get("/admin/branding").text
    assert "Paul · Couleur principale : « #FF7900 » → « #1F6FEB »" in page
    assert page.index("Couleur principale") < page.index("Paul · Nom de l&#39;application")


# --- Saisies malveillantes ---

@pytest.mark.parametrize("field, value", [
    ("color_primary", "red; background:url(https://evil.example/x.png)"),
    ("color_primary", "#FF7900;}body{display:none"),
    ("color_dark", "#111111</style><script>alert(1)</script>"),
    ("app_name", "<script>alert(1)</script>"),
    ("logo_part2", '<img src=x onerror="alert(1)">'),
    ("tagline_en", "Hello {app_name}"),
])
def test_injection_attempts_are_refused(admin, field, value):
    response = save(admin, **{field: value})
    assert response.status_code == 400
    assert "Certains champs sont à corriger." in response.text
    assert "<script>alert" not in response.text and "evil.example/x.png)" not in response.text.split("<form")[0]
    page = admin.get("/").text
    assert brand_variable(page, "--color-primary") == "#FF7900" and "MaxitProno" in title(page)


def test_quotes_and_ampersand_are_escaped(admin):
    save(admin, app_name='Tom & "Jerry"', logo_part1="Tom&Co")
    page = admin.get("/").text
    assert "<title>Accueil · Tom &amp; &#34;Jerry&#34;</title>" in page
    assert 'og:site_name" content="Tom &amp; &#34;Jerry&#34;"' in page
    assert "Tom&amp;Co" in page
