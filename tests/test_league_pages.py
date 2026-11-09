"""Pages des ligues : création, invitation par code et par lien, départ, admin."""
import re

from app.models import League, LeagueMember
from app.services.leagues import format_code


def register(client, nickname="Paul", next_url=None):
    data = {"nickname": nickname, "pin": "1234", "country_code": "CM", "rules_accepted": "true"}
    if next_url:
        data["next"] = next_url
    return client.post("/register", data=data, follow_redirects=False)


def logout(client):
    client.post("/logout")
    client.cookies.clear()


def create_league(client, name="Bureau Casa", **fields):
    response = client.post("/leagues", data={"name": name, **fields}, follow_redirects=False)
    assert response.status_code == 303
    page = client.get(response.headers["location"]).text  # écran « Ta ligue est prête »
    code = re.search(r'class="lg-code-big">([A-Z0-9]{3})-([A-Z0-9]{3})</strong>', page).groups()
    league_id = int(response.headers["location"].split("/")[2].split("?")[0])
    return league_id, "".join(code)


def test_leagues_page_requires_login(client):
    response = client.get("/leagues", follow_redirects=False)
    assert response.headers["location"] == "/login?next=/leagues"


def test_create_league_shows_code_and_invite_buttons(client):
    register(client)
    league_id, code = create_league(client)
    page = client.get(f"/leagues/{league_id}").text
    assert "Bureau Casa" in page and format_code(code) in page
    assert f"/j/{code}?ref=1" in page
    assert "https://wa.me/?text=" in page and "Bureau%20Casa" in page
    assert "Inviter par WhatsApp" in page
    assert "Supprimer la ligue" in page  # l'admin peut supprimer
    assert "Bureau Casa" in client.get("/leagues").text


def test_create_league_with_bad_name_shows_error(client):
    register(client)
    response = client.post("/leagues", data={"name": "ab"})
    assert response.status_code == 400
    assert "entre 3 et 30 caractères" in response.text


def test_join_with_code_typed_in_lowercase(client):
    register(client)
    league_id, code = create_league(client)
    logout(client)
    register(client, "Awa")
    response = client.post("/leagues/join", data={"code": code.lower()}, follow_redirects=False)
    assert response.headers["location"] == f"/leagues/{league_id}?joined=1"
    page = client.get(f"/leagues/{league_id}").text
    assert "Paul" in page and "Quitter la ligue" in page and "Supprimer la ligue" not in page


def test_unknown_code_shows_error(client):
    register(client)
    response = client.post("/leagues/join", data={"code": "ZZZZZZ"})
    assert response.status_code == 400
    assert "Aucune ligue" in response.text


def test_join_link_get_never_joins(client):
    register(client)
    league_id, code = create_league(client)
    logout(client)
    register(client, "Awa")
    page = client.get(f"/join/{code}")
    assert page.status_code == 200
    assert "Bureau Casa" in page.text and "créée par Paul" in page.text
    assert client.get(f"/leagues/{league_id}").status_code == 404  # pas encore membre


def test_join_link_without_account_brings_back_after_sign_up(client):
    register(client)
    league_id, code = create_league(client)
    logout(client)

    page = client.get(f"/join/{code}").text
    assert f"/register?next=/join/{code}" in page
    response = register(client, "Awa", next_url=f"/join/{code}")
    assert response.headers["location"] == f"/leagues/{league_id}?joined=1"  # rejoint d'office
    assert "Bienvenue dans la ligue" in client.get(response.headers["location"]).text


def test_join_link_when_already_member_goes_to_league(client):
    register(client)
    league_id, code = create_league(client)
    response = client.get(f"/join/{code}", follow_redirects=False)
    assert response.headers["location"] == f"/leagues/{league_id}"


def test_unknown_join_link_is_404(client):
    assert client.get("/join/ZZZZZZ").status_code == 404


def test_login_keeps_next_and_refuses_other_sites(client):
    register(client)
    logout(client)
    response = client.post("/login", data={"nickname": "Paul", "pin": "1234",
                                           "next": "https://evil.example"},
                           follow_redirects=False)
    assert response.headers["location"] == "/"
    logout(client)
    assert 'name="next" value="/join/ABC"' in client.get("/login?next=/join/ABC").text


def test_non_member_gets_404(client):
    register(client)
    league_id, _ = create_league(client)
    logout(client)
    register(client, "Awa")
    assert client.get(f"/leagues/{league_id}").status_code == 404
    assert client.post(f"/leagues/{league_id}/delete", data={"confirm": "yes"}).status_code == 404


def test_member_leaves(client):
    register(client)
    league_id, code = create_league(client)
    logout(client)
    register(client, "Awa")
    client.post(f"/join/{code}")
    response = client.post(f"/leagues/{league_id}/leave", follow_redirects=False)
    assert response.headers["location"] == "/leagues?done=left"
    assert "Tu as quitté la ligue" in client.get("/leagues?done=left").text


def test_owner_cannot_leave(client):
    register(client)
    league_id, _ = create_league(client)
    response = client.post(f"/leagues/{league_id}/leave")
    assert response.status_code == 403
    assert "ne peut pas quitter" in response.text


def test_owner_removes_member_and_member_cannot_remove(client):
    register(client)
    league_id, code = create_league(client)
    logout(client)
    register(client, "Awa")
    client.post(f"/join/{code}")
    assert client.post(f"/leagues/{league_id}/members/1/remove").status_code == 403
    logout(client)
    client.post("/login", data={"nickname": "Paul", "pin": "1234"})
    page = client.get(f"/leagues/{league_id}/settings").text
    assert "Retirer" in page and "Awa" in page
    response = client.post(f"/leagues/{league_id}/members/2/remove", follow_redirects=False)
    assert response.status_code == 303
    assert "Awa" not in client.get(f"/leagues/{league_id}/settings").text


def test_delete_needs_confirmation(client):
    register(client)
    league_id, _ = create_league(client)
    assert client.post(f"/leagues/{league_id}/delete").status_code == 400
    response = client.post(f"/leagues/{league_id}/delete", data={"confirm": "yes"},
                           follow_redirects=False)
    assert response.headers["location"] == "/leagues?done=deleted"
    assert client.get(f"/leagues/{league_id}").status_code == 404
