"""Pourcentages 1 / N / 2 et écussons sur les cartes de match."""
from app.models import Prediction, User
from app.models.match import MatchStatus
from app.models.types import utc_now
from app.services.probabilities import MIN_PREDICTIONS_FOR_TRENDS
from tests.test_match_pages import login, add_match, db_session  # noqa: F401


def add_predictions(db, match, scores):
    for i, (home, away) in enumerate(scores):
        user = User(nickname=f"J{i}", nickname_key=f"j{i}", pin_hash="x", country_code="CM",
                    rules_accepted_at=utc_now())
        db.add(user)
        db.flush()
        db.add(Prediction(user_id=user.id, match_id=match.id, home_score=home, away_score=away))
    db.commit()


def test_players_trend_bar_from_threshold(client, db_session):
    login(client)  # page privée : joueur connecté
    match = add_match(db_session, 24)
    add_predictions(db_session, match, [(2, 0)] * 3 + [(1, 1)] + [(0, 1)])
    page = client.get("/matches?status=all").text
    assert 'class="mc-trend-bar"' in page
    assert "LIO 60 % · Nul 20 % · ÉTA 20 %" in page
    assert "victoire Lions 60 %, nul 20 %, victoire Étalons 20 %" in page  # version lue à voix haute


def test_trend_uses_players_not_provider(client, db_session):
    login(client)  # page privée : joueur connecté
    match = add_match(db_session, 24)
    match.prob_home, match.prob_draw, match.prob_away = 55, 26, 19
    db_session.commit()
    add_predictions(db_session, match, [(0, 1)] * 5)
    page = client.get("/matches?status=all").text
    assert "LIO 0 % · Nul 0 % · ÉTA 100 %" in page and "55 %" not in page


def test_neutral_bar_without_any_prediction(client, db_session):
    login(client)  # page privée : joueur connecté
    add_match(db_session, 24)
    page = client.get("/matches").text
    assert 'class="mc-trend-bar mc-trend-empty"' in page  # 3 parts égales
    assert "Aucun prono pour l&#39;instant" in page
    assert 'class="mc-trend-bar"' not in page


def test_real_bar_from_first_prediction(client, db_session):
    login(client)  # page privée : joueur connecté
    match = add_match(db_session, 24)
    add_predictions(db_session, match, [(2, 0)] * MIN_PREDICTIONS_FOR_TRENDS)
    page = client.get("/matches").text
    assert 'class="mc-trend-bar"' in page and "LIO 100 % · Nul 0 % · ÉTA 0 %" in page


def test_no_trend_on_closed_match(client, db_session):
    match = add_match(db_session, -1, status=MatchStatus.LIVE, score=(1, 0))
    add_predictions(db_session, match, [(2, 0)] * 6)
    assert 'class="mc-trend' not in client.get("/matches?status=all").text


def test_crest_shows_logo_with_initials_underneath(client, db_session):
    login(client)  # page privée : joueur connecté
    match = add_match(db_session, 24, home="Paris Saint-Germain", away="Marseille")
    match.home_logo_url = "https://crests.football-data.org/524.png"
    db_session.commit()
    page = client.get("/matches").text
    assert '<img src="https://crests.football-data.org/524.png"' in page
    assert 'loading="lazy"' in page
    assert '<span class="crest-initials">PSG</span>' in page
    assert '<span class="crest-initials">MAR</span>' in page
    assert page.count("<img src=") == 1  # pas de logo pour Marseille : initiales seules


def test_result_page_shows_crests(client, db_session):
    login(client)  # page privée : joueur connecté
    match = add_match(db_session, -3, home="Coton Sport", away="Canon",
                      status=MatchStatus.FINISHED, score=(2, 1))
    page = client.get(f"/results/{match.id}").text
    assert '<span class="crest-initials">CS</span>' in page
