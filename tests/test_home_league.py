"""Accueil « Ma ligue » et onglet Ligue des classements."""
import re

from tests.test_league_pages import create_league, logout, register


def test_home_without_league_invites_to_create_one(client):
    register(client)
    page = client.get("/").text
    assert "Joue avec tes potes" in page and 'href="/leagues"' in page
    assert "league-picker" not in page


def test_home_shows_selected_league_with_feed_and_invite(client):
    register(client)
    league_id, code = create_league(client, "Bureau Casa")
    page = client.get("/").text
    assert 'class="league-picker"' in page and "Bureau Casa" in page
    assert "Dans la ligue" in page and "a créé la ligue" in page
    assert "Inviter des potes par WhatsApp" in page and f"/join/{code}" in page
    assert "1 joueur" in page


def test_league_picker_switches_and_remembers_league(client):
    register(client)
    first_id, _ = create_league(client, "Première")
    second_id, _ = create_league(client, "Seconde")
    # Par défaut : la plus récemment rejointe
    assert re.search(r'league-picker-name">Seconde<', client.get("/").text)

    response = client.get(f"/?league={first_id}")
    assert re.search(r'league-picker-name">Première<', response.text)
    assert response.cookies.get("league") == str(first_id)
    assert re.search(r'league-picker-name">Première<', client.get("/").text)  # mémorisée


def test_league_picker_ignores_league_of_others(client):
    register(client)
    other_id, _ = create_league(client, "Pas à moi")
    logout(client)
    register(client, "Awa")
    page = client.get(f"/?league={other_id}").text
    assert "Pas à moi" not in page


def test_home_counts_league_members_and_feed_shows_arrival(client):
    register(client)
    _, code = create_league(client, "Bureau Casa")
    logout(client)
    register(client, "Awa")
    client.post(f"/join/{code}")
    page = client.get("/").text
    assert "2 joueurs" in page
    assert "<strong>Toi</strong>" in page and "a rejoint la ligue" in page
    assert "Paul</strong>" in page


def test_leaderboard_opens_on_league_tab_for_members(client):
    register(client)
    create_league(client, "Bureau Casa")
    page = client.get("/leaderboard").text
    assert re.search(r'tab=league" class="active"', page)
    assert "depuis l&#39;arrivée" in page or "depuis l'arrivée" in page


def test_leaderboard_league_tab_without_league(client):
    register(client)
    page = client.get("/leaderboard?tab=league").text
    assert "Tu n&#39;es dans aucune ligue" in page or "Tu n'es dans aucune ligue" in page
    assert re.search(r'tab=general" class="active"', client.get("/leaderboard").text)
