"""Liens d'invitation personnels (?ref=) : qui a fait venir qui (badge Rassembleur)."""
import re

from app.models import LeagueMember, User
from app.services.leagues import valid_inviter
from tests.test_league_pages import create_league, logout, register
from tests.test_match_pages import db_session  # noqa: F401


def member(db, nickname):
    user = db.query(User).filter_by(nickname=nickname).one()
    db.expire_all()
    return db.query(LeagueMember).filter_by(user_id=user.id).one()


def test_valid_inviter():
    assert valid_inviter("1", [1, 2], joiner_id=3) == 1
    assert valid_inviter("9", [1, 2], joiner_id=3) is None  # pas membre
    assert valid_inviter("3", [1, 2], joiner_id=3) is None  # soi-même
    assert valid_inviter("abc", [1], joiner_id=3) is None
    assert valid_inviter(None, [1], joiner_id=3) is None


def test_league_page_shares_a_personal_link(client):
    register(client)
    league_id, code = create_league(client)
    page = client.get(f"/leagues/{league_id}").text
    assert f"/join/{code}?ref=1" in page


def test_ref_is_kept_through_sign_up(client, db_session):
    register(client)
    _, code = create_league(client)
    logout(client)
    page = client.get(f"/join/{code}?ref=1").text
    next_url = re.search(r'href="/register\?next=([^"]+)"', page).group(1)
    assert next_url == f"/join/{code}%3Fref%3D1"  # le parrain suit jusqu'au retour
    register(client, "Awa", next_url=f"/join/{code}?ref=1")
    page = client.get(f"/join/{code}?ref=1").text
    assert '<input type="hidden" name="ref" value="1">' in page
    client.post(f"/join/{code}", data={"ref": "1"})
    assert member(db_session, "Awa").invited_by_id == 1


def test_ref_of_a_non_member_is_ignored(client, db_session):
    register(client)
    _, code = create_league(client)
    logout(client)
    register(client, "Bob")  # pas membre de la ligue
    logout(client)
    register(client, "Awa")
    client.post(f"/join/{code}", data={"ref": "2"})
    assert member(db_session, "Awa").invited_by_id is None


def test_typed_code_has_no_inviter(client, db_session):
    register(client)
    _, code = create_league(client)
    logout(client)
    register(client, "Awa")
    client.post("/leagues/join", data={"code": code})
    assert member(db_session, "Awa").invited_by_id is None
