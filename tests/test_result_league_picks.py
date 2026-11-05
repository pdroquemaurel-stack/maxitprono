"""Match clôturé : carte « Les pronos de la ligue »."""
from datetime import timedelta
from types import SimpleNamespace

from app.models import Prediction, User
from app.models.match import MatchStatus
from app.models.types import utc_now
from app.routes.results import league_picks
from app.services.leagues import sort_league_predictions
from tests.test_league_pages import create_league, logout, register
from tests.test_match_pages import add_match, db_session  # noqa: F401


def pick(points):
    return SimpleNamespace(points=points)


def test_sort_puts_me_first_then_points_then_missing():
    rows = [(1, "Awa", pick(3)), (2, "Paul", pick(0)), (3, "Kevin", pick(5)),
            (4, "Sarah", None), (5, "moussa", pick(3)), (6, "Yacouba", pick(None))]
    order = [name for _, name, _ in sort_league_predictions(rows, me_id=2)]
    assert order == ["Paul", "Kevin", "Awa", "moussa", "Yacouba", "Sarah"]


def add_prediction(db, nickname, match, home, away, points, exact=False):
    user = db.query(User).filter_by(nickname=nickname).one()
    db.add(Prediction(user_id=user.id, match_id=match.id, home_score=home, away_score=away,
                      points=points, is_exact=exact, is_winner=points > 0))
    db.commit()


def setup_league(client):
    """Paul crée la ligue, Awa la rejoint, Moussa reste dehors ; Paul est connecté à la fin."""
    register(client)
    _, code = create_league(client, "Bureau Casa")
    logout(client)
    register(client, "Awa")
    client.post(f"/join/{code}")
    logout(client)
    register(client, "Moussa")
    logout(client)
    client.post("/login", data={"nickname": "Paul", "pin": "1234"})


def test_result_shows_league_members_predictions(client, db_session):
    setup_league(client)
    match = add_match(db_session, -3, status=MatchStatus.FINISHED, score=(2, 1))
    add_prediction(db_session, "Paul", match, 1, 0, 3)
    add_prediction(db_session, "Awa", match, 2, 1, 5, exact=True)
    add_prediction(db_session, "Moussa", match, 0, 2, 0)

    page = client.get(f"/results/{match.id}").text

    assert "Les pronos de la ligue" in page and "Bureau Casa" in page
    card = page[page.index("league-picks"):]
    assert card.index("Toi") < card.index("Awa")  # moi d'abord
    assert "Moussa" not in card  # pas membre
    assert "+5" in card and "+3" in card
    assert "après la clôture" in page


def test_member_without_prediction_is_listed(client, db_session):
    setup_league(client)
    match = add_match(db_session, -3, status=MatchStatus.FINISHED, score=(2, 1))
    add_prediction(db_session, "Paul", match, 2, 1, 5, exact=True)
    card = client.get(f"/results/{match.id}").text.split("league-picks", 1)[1]
    assert "Awa" in card and "pas de prono" in card


def test_no_card_without_league_or_when_logged_out(client, db_session):
    register(client)
    match = add_match(db_session, -3, status=MatchStatus.FINISHED, score=(2, 1))
    assert "Les pronos de la ligue" not in client.get(f"/results/{match.id}").text
    logout(client)
    assert "Les pronos de la ligue" not in client.get(f"/results/{match.id}").text


def test_no_league_picks_while_predictions_are_open(db_session):
    match = SimpleNamespace(id=1, status=MatchStatus.SCHEDULED,
                            kickoff_at=utc_now() + timedelta(days=1))
    request = SimpleNamespace(cookies={})
    user = SimpleNamespace(id=1)
    assert league_picks(request, db_session, user, match) == (None, [])
