"""Accueil du joueur connecté : salutation, pronos à faire, résultats d'hier, ligues, progression."""
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

from app.models import Prediction, RankSnapshot
from app.models.match import MatchStatus
from app.models.types import utc_now
from app.services.activity import Event, friends_feed
from app.services.home import badge_progress, local_day_bounds, places_gained
from app.services.probabilities import Probabilities, leading_outcome
from app.services.profile_stats import BADGE_GOALS, Badge
from tests.test_leaderboard_page import paul
from tests.test_match_pages import add_match, db_session, login, predict  # noqa: F401

NOW = datetime(2026, 11, 10, 12, 0, tzinfo=UTC)


# --- Fonctions pures ---

def test_places_gained_compares_with_previous_snapshot():
    ranks = [(date(2026, 11, 7), 9), (date(2026, 11, 8), 5), (date(2026, 11, 9), 3)]
    assert places_gained(ranks, date(2026, 11, 9)) == 2
    assert places_gained([(date(2026, 11, 8), 3), (date(2026, 11, 9), 6)], date(2026, 11, 9)) == -3
    assert places_gained(ranks, date(2026, 11, 10)) == 0  # pas de rang ce jour-là
    assert places_gained([(date(2026, 11, 9), 1)], date(2026, 11, 9)) == 0  # premier rang


def test_local_day_bounds_follow_the_player_timezone():
    start, end = local_day_bounds(date(2026, 11, 9), ZoneInfo("Africa/Douala"))  # UTC+1
    assert start == datetime(2026, 11, 8, 23, 0, tzinfo=UTC)
    assert end == datetime(2026, 11, 9, 23, 0, tzinfo=UTC)


def test_badge_progress_counts_what_is_done():
    assert badge_progress(Badge("prophet", "eye", 1), BADGE_GOALS) == (2, 3)


def test_leading_outcome_prefers_home_then_draw_on_ties():
    assert leading_outcome(Probabilities(62, 20, 18, "players")) == ("home", 62)
    assert leading_outcome(Probabilities(20, 30, 50, "provider")) == ("away", 50)
    assert leading_outcome(Probabilities(40, 40, 20, "players")) == ("home", 40)


def test_friends_feed_skips_me_and_duplicates_and_keeps_three():
    exact = Event("exact", "Awa", NOW, "A – B", user_id=2)
    events = [Event("joined", "Moi", NOW, user_id=1), exact, exact,  # même score exact, 2 ligues
              Event("joined", "Ali", NOW - timedelta(hours=1), user_id=3),
              Event("joined", "Bea", NOW - timedelta(hours=2), user_id=4),
              Event("joined", "Cyr", NOW - timedelta(hours=3), user_id=5)]
    feed = friends_feed(events, me_id=1)
    assert [e.nickname for e in feed] == ["Awa", "Ali", "Bea"]


# --- Page ---

def test_new_player_without_prediction(client):
    login(client)
    page = client.get("/").text
    assert "Salut Paul" in page and "Prêt pour les prochains matchs ?" in page
    assert '<strong class="h-kpi-value">0 %</strong>' in page and "Série : 0" in page
    assert "Mes résultats d" not in page  # rien hier : bloc masqué
    assert "Tous tes pronos sont prêts" in page and "Pas de match à venir" in page
    assert "Prochain badge" in page and "Rassembleur" in page and "0 sur 1" in page
    assert '<nav class="tabbar"' in page and 'href="/" class="active"' in page
    for absent in ("mode compétition", "Duel de la semaine", "Le podium"):
        assert absent not in page


def test_todo_block_shows_three_open_matches_with_save_button(client, db_session):
    for hours in (2, 5, 8, 11):
        add_match(db_session, hours, home="Lions", away="Paris Saint-Germain")
    login(client)
    page = client.get("/").text
    assert "4 pronos à faire" in page and "Le premier ferme dans" in page
    assert "Aujourd" in page or "Demain" in page
    todo = page[page.index('class="h-todo"'):page.index('href="/matches">Voir tous les matchs')]
    assert "À jouer maintenant" in page
    assert todo.count('class="card match-card"') == 3
    assert 'data-mode="button"' in todo and "data-save-all" in todo and "Valider mes pronos" in todo
    assert 'data-done-label="Pronos enregistrés"' in todo
    # Même gabarit que la page Pronos : abréviation, nom complet, cases de score, pas de + / –
    assert '<span class="team-name">Lions</span>' in todo
    assert '<span class="team-name">Paris Saint-Germain</span>' in todo
    assert 'data-score="home"' in todo and "<button type=\"button\" class=\"step" not in todo


def test_saving_from_home_uses_the_same_endpoint(client, db_session):
    match = add_match(db_session, 5)
    login(client)
    assert predict(client, match, "1", "1").json() == {"saved": True}
    assert "Tous tes pronos sont prêts" in client.get("/").text


def test_match_without_logo_falls_back_to_round_initials(client, db_session):
    match = add_match(db_session, 5, home="Coton Sport", away="Canon")
    match.away_logo_url = "https://crests.football-data.org/1.png"
    db_session.commit()
    login(client)
    page = client.get("/").text
    assert '<span class="crest-initials">CS</span>' in page
    assert page.count('<img src="https://crests.football-data.org/1.png"') == 1  # seul Canon a un logo


def test_yesterday_results_points_places_and_share(client, db_session):
    login(client)
    me = paul(db_session)
    exact = add_match(db_session, -24, home="Lions", away="Aigles",
                      status=MatchStatus.FINISHED, score=(2, 1))
    missed = add_match(db_session, -23, home="Fennecs", away="Éléphants",
                       status=MatchStatus.FINISHED, score=(0, 0))
    db_session.add_all([
        Prediction(user_id=me.id, match_id=exact.id, home_score=2, away_score=1,
                   points=5, is_exact=True, is_winner=True),
        Prediction(user_id=me.id, match_id=missed.id, home_score=1, away_score=0,
                   points=0, is_exact=False, is_winner=False)])
    yesterday = (utc_now() - timedelta(hours=24)).astimezone(ZoneInfo("Africa/Douala")).date()
    db_session.add_all([RankSnapshot(day=yesterday - timedelta(days=1), user_id=me.id, rank=5, points=0),
                        RankSnapshot(day=yesterday, user_id=me.id, rank=3, points=5)])
    db_session.commit()
    page = client.get("/").text
    assert 'Hier, tu as gagné <strong class="h-gain">5 pts</strong> et 2 places.' in page
    assert "+5 hier" in page
    assert "Mes résultats d" in page and "+5 pts" in page
    assert "Ton prono : 2 – 1" in page and "Ton prono : 1 – 0" in page
    assert '<span class="lg-pts exact">+5</span>' in page and '<span class="lg-pts miss">0</span>' in page
    assert "Score exact sur Lions – Aigles. Montre\u2011le\u00a0!" in page and "data-home-share" in page
    assert 'href="/results"' in page


def test_home_in_english(client):
    login(client)
    client.get("/language/en")
    page = client.get("/").text
    assert "Hi Paul" in page and "Ready for the next matches?" in page
