from app.models import Prediction, User
from app.models.match import MatchStatus
from tests.test_match_pages import add_match, db_session, login  # noqa: F401


def test_results_lists_recent_finished_matches_only(client, db_session):
    add_match(db_session, -3, home="Fini", status=MatchStatus.FINISHED, score=(2, 1))
    add_match(db_session, -24 * 20, home="Ancien", status=MatchStatus.FINISHED, score=(0, 0))
    add_match(db_session, 24, home="AVenir")
    page = client.get("/results").text
    assert "Fini" in page
    assert "Ancien" not in page and "AVenir" not in page


def test_results_colors_the_final_score(client, db_session):
    add_match(db_session, -3, status=MatchStatus.FINISHED, score=(2, 1))
    page = client.get("/results").text
    assert '<span class="win">2</span>' in page
    assert '<span class="lose">1</span>' in page


def test_results_show_my_prediction_and_exact_badge(client, db_session):
    login(client)
    match = add_match(db_session, -3, status=MatchStatus.FINISHED, score=(2, 1))
    paul = db_session.query(User).filter_by(nickname="Paul").one()
    db_session.add(Prediction(user_id=paul.id, match_id=match.id, home_score=2, away_score=1,
                              points=5, is_exact=True, is_winner=True))
    db_session.commit()
    page = client.get("/results").text
    assert "Mon pronostic" in page
    assert "badge points exact" in page and "+5" in page


def test_tabbar_marks_the_current_tab(client):
    page = client.get("/results").text
    assert 'href="/results" class="active" aria-current="page"' in page
    assert 'href="/login"' in page  # onglet Profil quand on n'est pas connecté
    for label in ("Ma ligue", "Pronos", "Classements", "Résultats", "Profil"):
        assert label in page


def test_result_page_shows_exact_score_banner(client, db_session):
    login(client)
    match = add_match(db_session, -3, status=MatchStatus.FINISHED, score=(2, 1))
    paul = db_session.query(User).filter_by(nickname="Paul").one()
    db_session.add(Prediction(user_id=paul.id, match_id=match.id, home_score=2, away_score=1,
                              points=5, is_exact=True, is_winner=True))
    db_session.commit()
    assert f'href="/results/{match.id}"' in client.get("/results").text
    page = client.get(f"/results/{match.id}").text
    assert "Ton prono : 2 – 1, score exact !" in page and "+5" in page


def test_result_page_without_prediction(client, db_session):
    login(client)
    match = add_match(db_session, -3, status=MatchStatus.FINISHED, score=(0, 0))
    assert "pas pronostiqué" in client.get(f"/results/{match.id}").text


def test_result_page_only_for_done_matches(client, db_session):
    match = add_match(db_session, 24)
    assert client.get(f"/results/{match.id}").status_code == 404
    assert client.get("/results/9999").status_code == 404
