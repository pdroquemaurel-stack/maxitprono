"""Accueil « Ma ligue » et onglet Ligue des classements."""
import re

from tests.test_league_pages import create_league, logout, register


def test_home_without_league_shows_join_card_and_create_tile(client):
    register(client)
    page = client.get("/").text
    assert "Ma ligue" in page and "Rejoindre" in page  # mini-carte vers /leagues
    assert 'class="h-league h-league-new" href="/leagues"' in page
    assert "Chez les copains" not in page  # pas de données : bloc masqué


def test_home_lists_all_my_leagues_in_carousel(client):
    register(client)
    first_id, _ = create_league(client, "Première")
    second_id, _ = create_league(client, "Seconde")
    page = client.get("/").text
    assert f'href="/leagues/{first_id}"' in page and f'href="/leagues/{second_id}"' in page
    assert page.count('class="h-card h-league"') == 2
    assert "1 membre" in page


def test_opening_a_league_makes_it_the_main_league(client):
    register(client)
    first_id, _ = create_league(client, "Première")
    second_id, _ = create_league(client, "Seconde")
    # Par défaut : la plus récemment rejointe
    assert re.search(rf'class="h-kpi" href="/leagues/{second_id}">\s*<span class="h-kpi-label">Seconde<',
                     client.get("/").text)
    response = client.get(f"/leagues/{first_id}")
    assert response.cookies.get("league") == str(first_id)
    assert re.search(r'h-kpi-label">Première<', client.get("/").text)
    # L'ancien lien « ?league= » marche encore
    client.get(f"/?league={second_id}")
    assert re.search(r'h-kpi-label">Seconde<', client.get("/").text)


def test_home_ignores_league_of_others(client):
    register(client)
    other_id, _ = create_league(client, "Pas à moi")
    logout(client)
    register(client, "Awa")
    page = client.get(f"/?league={other_id}").text
    assert "Pas à moi" not in page


def test_friends_feed_shows_others_but_not_me(client):
    register(client)
    _, code = create_league(client, "Bureau Casa")
    logout(client)
    register(client, "Awa")
    client.post(f"/join/{code}")
    page = client.get("/").text
    feed = page[page.index("Chez les copains"):]
    assert "<strong>Paul</strong>" in feed and "a créé la ligue" in feed
    assert "<strong>Awa</strong>" not in feed  # mes propres événements ne sont pas repris


def test_leaderboard_opens_on_league_tab_for_members(client):
    register(client)
    create_league(client, "Bureau Casa")
    page = client.get("/leaderboard").text
    assert re.search(r'class="chip active" href="/leaderboard\?tab=league"', page)
    assert "depuis l&#39;arrivée" in page or "depuis l'arrivée" in page


def test_leaderboard_league_tab_without_league(client):
    register(client)
    page = client.get("/leaderboard?tab=league").text
    assert "Tu n&#39;es dans aucune ligue" in page or "Tu n'es dans aucune ligue" in page
    assert re.search(r'class="chip active" href="/leaderboard\?tab=general"', client.get("/leaderboard").text)
