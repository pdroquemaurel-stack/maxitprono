from datetime import timedelta

import pytest

from app.models import Prediction, User
from app.models.match import MatchStatus
from app.models.types import utc_now
from tests.test_match_pages import add_match, db_session, login  # noqa: F401


def add_player(db, nickname, country="CM"):
    user = User(nickname=nickname, nickname_key=nickname.lower(), pin_hash="x",
                country_code=country, rules_accepted_at=utc_now(),
                created_at=utc_now() - timedelta(days=30))
    db.add(user)
    db.commit()
    return user


def add_scored(db, user, points, hours_ago=2, name="Ligue 1", exact=False):
    match = add_match(db, -hours_ago, status=MatchStatus.FINISHED, score=(1, 0), name=name)
    db.add(Prediction(user_id=user.id, match_id=match.id, home_score=1, away_score=0,
                      points=points, is_exact=exact, is_winner=points > 0))
    db.commit()
    return match


def paul(db):
    return db.query(User).filter_by(nickname_key="paul").one()


def test_general_leaderboard_lists_players_in_order(client, db_session):
    add_scored(db_session, add_player(db_session, "Ali"), 3)
    add_scored(db_session, add_player(db_session, "Bea"), 5, exact=True)

    text = client.get("/leaderboard").text

    assert "Classements" in text
    assert text.index("Bea") < text.index("Ali")


def test_empty_leaderboard(client):
    assert "Pas encore de classement" in client.get("/leaderboard").text


def test_logged_in_player_sees_own_rank(client, db_session):
    add_scored(db_session, add_player(db_session, "Ali"), 5)
    login(client)
    assert "Pas encore classé" in client.get("/leaderboard").text

    add_scored(db_session, paul(db_session), 3)
    assert "Ton rang : 2 sur 2 · 3 pts" in client.get("/leaderboard").text


def test_player_outside_top_is_shown_at_the_bottom(client, db_session, monkeypatch):
    monkeypatch.setattr("app.routes.leaderboard.TOP_COUNT", 1)
    add_scored(db_session, add_player(db_session, "Ali"), 5)
    login(client)
    add_scored(db_session, paul(db_session), 3)

    text = client.get("/leaderboard").text

    assert 'class="rank-row me"' in text and "<strong>Toi</strong>" in text
    assert 'class="gap"' in text
    assert '<span class="rank first">1</span>' in text  # Ali, en tête
    assert "0 score exact" in text


def test_country_tab_defaults_to_player_country(client, db_session):
    add_scored(db_session, add_player(db_session, "Ali", "CM"), 3)
    add_scored(db_session, add_player(db_session, "Cyr", "BF"), 5)
    login(client)  # Paul est au Cameroun

    text = client.get("/leaderboard?tab=country").text
    assert "Ali" in text and "Cyr" not in text

    text = client.get("/leaderboard?tab=country&country=BF").text
    assert "Cyr" in text and "Ali" not in text


def test_competition_tab(client, db_session):
    ali, cyr = add_player(db_session, "Ali"), add_player(db_session, "Cyr")
    match = add_scored(db_session, ali, 3, name="Ligue 1")
    add_scored(db_session, cyr, 5, name="CAN")

    text = client.get(f"/leaderboard?tab=competition&competition={match.competition_id}").text

    assert "Ali" in text and "Cyr" not in text


def test_week_tab_shows_current_week_only(client, db_session):
    add_scored(db_session, add_player(db_session, "Ali"), 3, hours_ago=0)
    add_scored(db_session, add_player(db_session, "Old"), 5, hours_ago=24 * 8)

    text = client.get("/leaderboard?tab=week").text

    assert "Ali" in text and "Old" not in text


@pytest.mark.parametrize("query", ["?tab=nope", "?tab=week&week=bad", "?tab=country&country=XX",
                                   "?tab=competition&competition=abc"])
def test_bad_parameters_do_not_crash(client, query):
    assert client.get(f"/leaderboard{query}").status_code == 200


def test_home_shows_my_points(client, db_session):
    login(client)
    add_scored(db_session, paul(db_session), 5, hours_ago=24 * 3)
    page = client.get("/").text
    assert '<strong class="h-kpi-value">5</strong>' in page


def test_history_shows_points(client, db_session):
    login(client)
    add_scored(db_session, paul(db_session), 5)
    assert "+5" in client.get("/profile/history").text
