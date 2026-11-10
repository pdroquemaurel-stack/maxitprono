"""Accueil du visiteur non connecté, compte à rebours, compétition du moment, pages « à venir »."""
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from app.i18n import format_countdown
from app.models.types import utc_now
from app.services.game_settings import Settings
from app.services.settings_store import save_settings
from app.services.deadlines import countdown_to_closing
from app.services.home import featured_competition
from tests.test_match_pages import add_match, db_session  # noqa: F401 (fixture)

NOW = datetime(2026, 11, 10, 12, 0, tzinfo=UTC)


# --- Fonctions pures ---

def test_countdown_to_closing_counts_until_ten_minutes_before_kickoff():
    left = countdown_to_closing(NOW + timedelta(hours=2, minutes=10), NOW)
    assert (left.days, left.hours, left.minutes) == (0, 2, 0)
    left = countdown_to_closing(NOW + timedelta(days=2, hours=4, minutes=10), NOW)
    assert (left.days, left.hours) == (2, 4)
    assert countdown_to_closing(NOW, NOW).minutes == 1  # jamais « 0 min »


def test_format_countdown_in_french_and_english():
    assert format_countdown(NOW + timedelta(hours=1, minutes=52), NOW, "fr") == "1 h 42"
    assert format_countdown(NOW + timedelta(minutes=18), NOW, "en") == "8 min"
    assert format_countdown(NOW + timedelta(days=3, minutes=10), NOW, "fr") == "3 j 0 h"


@dataclass
class FakeCompetition:
    id: int
    name: str


@dataclass
class FakeMatch:
    competition: FakeCompetition
    kickoff_at: datetime


def test_featured_competition_has_most_matches_this_week():
    cl, ligue1 = FakeCompetition(1, "Ligue des champions"), FakeCompetition(2, "Ligue 1")
    matches = [FakeMatch(ligue1, NOW + timedelta(hours=1)),
               FakeMatch(cl, NOW + timedelta(hours=2)), FakeMatch(cl, NOW + timedelta(hours=3)),
               FakeMatch(ligue1, NOW + timedelta(days=9))]  # hors des 7 jours
    assert featured_competition(matches, NOW) is cl


def test_featured_competition_tie_goes_to_the_next_match_and_none_without_matches():
    cl, ligue1 = FakeCompetition(1, "CL"), FakeCompetition(2, "L1")
    matches = [FakeMatch(ligue1, NOW + timedelta(hours=1)), FakeMatch(cl, NOW + timedelta(hours=2))]
    assert featured_competition(matches, NOW) is ligue1
    assert featured_competition([], NOW) is None


# --- Page ---

def test_guest_home_shows_hero_steps_and_footer_without_tabbar(client):
    page = client.get("/").text
    assert "Pronostique les scores." in page and "Défie tes amis." in page
    assert 'href="/register"' in page and "Jouer gratuitement" in page
    assert 'href="/login"' in page and "déjà un compte" in page
    assert "+5 score exact" in page and "+3 bon résultat" in page  # barème par défaut (3 + 2)
    for href in ("/rules", "/help", "/privacy", "/legal"):
        assert f'href="{href}"' in page
    assert "sans mise d&#39;argent" in page
    assert '<nav class="tabbar"' not in page
    assert "Plus drôle entre amis" not in page and "Tous les matchs" not in page


def test_guest_home_uses_game_scoring_settings(client, db_session):
    save_settings(db_session, Settings(winner_points=2, exact_bonus=3, league_max_members=100),
                  utc_now())
    page = client.get("/").text
    assert "+5 score exact" in page and "+2 bon résultat" in page


def test_guest_home_lists_next_three_open_matches_linking_to_register(client, db_session):
    add_match(db_session, -1, home="Commencé")  # déjà fermé
    for hours, home in ((2, "Premier"), (5, "Deuxième"), (8, "Troisième"), (11, "Quatrième")):
        add_match(db_session, hours, home=home)
    page = client.get("/").text
    assert "À pronostiquer" in page
    assert "Premier" in page and "Troisième" in page
    assert "Quatrième" not in page and "Commencé" not in page
    assert page.count('class="hg-match" href="/register"') == 3
    assert page.count("data-countdown=") == 1  # seulement le plus proche


def test_guest_home_shows_competition_of_the_moment(client, db_session):
    add_match(db_session, 3, name="Ligue des champions")
    add_match(db_session, 4, name="Ligue des champions")
    add_match(db_session, 2, name="Ligue 1")
    page = client.get("/").text
    assert "EN CE MOMENT" in page
    featured = page[page.index('class="hg-featured"'):]
    assert "Ligue des champions" in featured[:300] and "Je participe" in featured


def test_guest_home_without_matches_hides_match_blocks(client):
    page = client.get("/").text
    assert "À pronostiquer" not in page and "EN CE MOMENT" not in page


def test_guest_home_in_english(client):
    client.get("/language/en")
    page = client.get("/").text
    assert "Predict the scores." in page and "Play for free" in page


def test_footer_pages_say_coming_soon(client):
    for path, title in (("/help", "Aide"), ("/privacy", "Confidentialité"), ("/legal", "Mentions légales")):
        page = client.get(path)
        assert page.status_code == 200
        assert title in page.text and "Contenu à venir" in page.text
