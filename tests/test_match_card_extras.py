"""Pourcentages 1 / N / 2 et écussons sur les cartes de match."""
from app.models import Prediction, User
from app.models.match import MatchStatus
from app.models.types import utc_now
from app.services.probabilities import MIN_PREDICTIONS_FOR_TRENDS
from tests.test_match_pages import add_match, db_session  # noqa: F401


def add_predictions(db, match, scores):
    for i, (home, away) in enumerate(scores):
        user = User(nickname=f"J{i}", nickname_key=f"j{i}", pin_hash="x", country_code="CM",
                    rules_accepted_at=utc_now())
        db.add(user)
        db.flush()
        db.add(Prediction(user_id=user.id, match_id=match.id, home_score=home, away_score=away))
    db.commit()


def test_provider_percentages_are_shown(client, db_session):
    match = add_match(db_session, 24)
    match.prob_home, match.prob_draw, match.prob_away = 55, 26, 19
    db_session.commit()
    page = client.get("/matches").text
    assert "1 <b>55 %</b>" in page and "N <b>26 %</b>" in page and "2 <b>19 %</b>" in page
    assert "Tendance des joueurs" not in page


def test_player_trends_shown_from_threshold(client, db_session):
    match = add_match(db_session, 24)
    add_predictions(db_session, match, [(2, 0)] * 3 + [(1, 1)] + [(0, 1)])
    page = client.get("/matches").text
    assert "Tendance des joueurs" in page
    assert "1 <b>60 %</b>" in page and "N <b>20 %</b>" in page and "2 <b>20 %</b>" in page


def test_no_percentages_below_threshold(client, db_session):
    match = add_match(db_session, 24)
    add_predictions(db_session, match, [(2, 0)] * (MIN_PREDICTIONS_FOR_TRENDS - 1))
    assert 'class="probs"' not in client.get("/matches").text


def test_crest_shows_logo_with_initials_underneath(client, db_session):
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
    match = add_match(db_session, -3, home="Coton Sport", away="Canon",
                      status=MatchStatus.FINISHED, score=(2, 1))
    page = client.get(f"/results/{match.id}").text
    assert '<span class="crest-initials">CS</span>' in page
