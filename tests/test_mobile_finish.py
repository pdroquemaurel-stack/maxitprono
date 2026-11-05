"""Finitions mobile : compression, cache des fichiers statiques, icônes, écussons des résultats."""
import re

from app.models.match import MatchStatus
from app.templating import static_url
from tests.test_league_pages import register
from tests.test_match_pages import add_match, db_session  # noqa: F401


def test_pages_are_compressed(client, db_session):
    for hours in range(1, 30, 3):
        add_match(db_session, hours)
    response = client.get("/matches", headers={"Accept-Encoding": "gzip"})
    assert response.headers["content-encoding"] == "gzip"


def test_static_url_has_a_version_that_follows_the_content():
    url = static_url("css/style.css")
    assert re.fullmatch(r"/static/css/style\.css\?v=[0-9a-f]{8}", url)
    assert static_url("css/style.css") == url


def test_versioned_static_files_are_cached_one_year(client):
    response = client.get(static_url("css/style.css"))
    assert response.headers["cache-control"] == "public, max-age=31536000, immutable"
    assert "immutable" not in client.get("/static/css/style.css").headers.get("cache-control", "")
    assert "immutable" in client.get("/static/fonts/outfit.woff2").headers["cache-control"]


def test_pages_use_versioned_css_and_plain_font_urls(client):
    page = client.get("/").text
    assert static_url("css/style.css") in page
    assert 'href="/static/fonts/outfit.woff2"' in page  # même adresse que dans le CSS


def test_icons_and_theme_color(client):
    page = client.get("/").text
    assert 'rel="icon"' in page and 'rel="apple-touch-icon"' in page
    assert '<meta name="theme-color" content="#F6F7FB">' in page
    favicon = client.get("/favicon.ico")
    assert favicon.status_code == 200 and favicon.headers["content-type"] == "image/png"


def test_results_list_shows_crests(client, db_session):
    match = add_match(db_session, -3, home="Coton Sport", away="Canon",
                      status=MatchStatus.FINISHED, score=(2, 1))
    match.home_logo_url = "https://crests.example/coton.png"
    db_session.commit()
    page = client.get("/results").text
    assert '<img src="https://crests.example/coton.png"' in page
    assert '<span class="crest-initials">CAN</span>' in page


def test_short_competition_tab(client):
    register(client)
    assert ">Compét.<" in client.get("/leaderboard").text
