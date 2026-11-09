"""Page Profil (statistiques), « Modifier mon profil » et historique."""
from datetime import timedelta

from app.models import Prediction, User
from app.models.match import MatchStatus
from app.models.types import utc_now
from tests.test_league_pages import create_league, logout, register
from tests.test_match_pages import add_match, db_session  # noqa: F401


def paul(db):
    return db.query(User).filter_by(nickname_key="paul").one()


def add_pick(db, user, pred, real, hours_ago=2, name="Ligue 1"):
    """Prono déjà noté sur un match terminé (barème par défaut : 3 + 2)."""
    match = add_match(db, -hours_ago, status=MatchStatus.FINISHED, score=real, name=name)
    is_exact = tuple(pred) == tuple(real)
    is_winner = (pred[0] > pred[1]) - (pred[0] < pred[1]) == (real[0] > real[1]) - (real[0] < real[1])
    db.add(Prediction(user_id=user.id, match_id=match.id, home_score=pred[0], away_score=pred[1],
                      points=3 * is_winner + 2 * is_exact, is_exact=is_exact, is_winner=is_winner))
    db.commit()
    return match


# --- Compte sans prono ---

def test_profile_without_predictions(client):
    register(client)
    page = client.get("/profile").text
    assert "Fais ton premier prono !" in page
    assert "0 %" in page and "Pronos joués" in page
    assert page.count('href="/profile/edit"') == 2  # engrenage + bouton « Modifier »
    assert "Pas encore de prono sur un match terminé." in page
    assert "Prochain : Rassembleur" in page  # 1 ami suffit : le badge le plus proche
    assert '<a href="/profile" class="active" aria-current="page">' in page  # onglet Profil actif


def test_profile_shows_identity(client):
    register(client)
    page = client.get("/profile").text
    assert "<h1>Paul</h1>" in page and "Cameroun" in page and "Membre depuis" in page
    assert 'class="p-avatar p-initials"' in page and ">PA<" in page


# --- Compte avec plusieurs pronos ---

def test_profile_with_predictions(client, db_session):
    register(client)
    user = paul(db_session)
    add_pick(db_session, user, (2, 1), (2, 1), hours_ago=5)  # exact, 5 pts
    add_pick(db_session, user, (1, 0), (3, 1), hours_ago=4)  # bon résultat, 3 pts
    add_pick(db_session, user, (0, 0), (1, 0), hours_ago=3)  # raté
    add_match(db_session, 24)  # match à venir : ne compte pas
    page = client.get("/profile").text
    assert "Fais ton premier prono" not in page
    assert "67 %" in page  # 2 réussis sur 3
    assert '<p class="p-hero-points">8</p>' in page
    assert "2,7 pt par prono" in page
    assert page.count('<li class="p-form-') == 3  # une case par prono joué
    assert "3 pronos · 67 %" in page
    assert "Série en cours" in page


def test_week_period_only_counts_this_week(client, db_session):
    register(client)
    add_pick(db_session, paul(db_session), (2, 1), (2, 1), hours_ago=24 * 10)
    assert "100 %" in client.get("/profile?period=season").text
    week = client.get("/profile?period=week").text
    assert "Semaine du" in week and "Fais ton premier prono !" in week


def test_competition_period_defaults_to_champions_league(client, db_session):
    register(client)
    add_pick(db_session, paul(db_session), (2, 1), (2, 1), name="Ligue 1")
    add_pick(db_session, paul(db_session), (0, 1), (2, 1), name="Ligue des champions")
    page = client.get("/profile?period=competition").text
    hero_line = page.split('class="p-hero-sub">')[1].split("</p>")[0]
    assert "Ligue des champions" in hero_line
    assert "0 %" in page
    ligue_1 = page.split('value="')[1].split('"')[0]  # 1re option de la liste
    assert "100 %" in client.get(f"/profile?period=competition&competition={ligue_1}").text


def test_strongest_competition_needs_five_predictions(client, db_session):
    register(client)
    for hours in range(2, 7):
        add_pick(db_session, paul(db_session), (1, 0), (2, 0), hours_ago=hours, name="Liga")
    assert "Ta compétition forte :" in client.get("/profile").text


def test_prophet_badge_after_three_exact_scores(client, db_session):
    register(client)
    assert 'class="unlocked"' not in client.get("/profile").text
    for hours in (2, 3, 4):
        add_pick(db_session, paul(db_session), (1, 0), (1, 0), hours_ago=hours)
    page = client.get("/profile").text
    assert page.count('class="unlocked"') == 1 and "1 / 4" in page


def test_league_card_badge_and_challenge_button(client, db_session):
    register(client)
    league_id, code = create_league(client)
    page = client.get("/profile").text
    assert "Bureau Casa" in page and "https://wa.me/?text=" in page  # « Défier un ami »
    logout(client)
    register(client, "Awa")
    client.post(f"/join/{code}", data={"ref": str(paul(db_session).id)})  # lien de Paul
    logout(client)
    client.post("/login", data={"nickname": "Paul", "pin": "1234"})
    add_pick(db_session, paul(db_session), (1, 0), (1, 0), hours_ago=-1)  # commencé après l'arrivée
    page = client.get("/profile").text
    assert "1<small>/2</small>" in page  # 1er de la ligue sur 2 membres
    assert "1 / 4" in page  # Rassembleur débloqué


def test_profile_in_english(client):
    register(client)
    client.get("/language/en")
    page = client.get("/profile").text
    assert "Share my stats" in page and "Make your first prediction!" in page


# --- Modifier mon profil ---

def test_edit_page_gathers_every_profile_function(client):
    register(client)
    page = client.get("/profile/edit").text
    for expected in ('name="avatar_file"', 'id="avatar_preview"', 'name="nickname"',
                     'name="country_code"', "/language/en", 'href="/profile/history"',
                     'href="/leagues"', 'href="/rules"', 'action="/logout"'):
        assert expected in page, expected
    assert 'href="/admin"' not in page


def test_edit_requires_login(client):
    response = client.get("/profile/edit", follow_redirects=False)
    assert response.headers["location"] == "/login?next=/profile/edit"


def test_change_nickname_then_log_in_with_it(client):
    register(client)
    response = client.post("/profile", data={"nickname": "Paulo", "country_code": "BF"})
    assert "Profil enregistré" in response.text and 'value="Paulo"' in response.text
    logout(client)
    response = client.post("/login", data={"nickname": "paulo", "pin": "1234"},
                           follow_redirects=False)
    assert response.status_code == 303


def test_nickname_already_taken(client, db_session):
    register(client, "Awa")
    logout(client)
    register(client)
    response = client.post("/profile", data={"nickname": "awa", "country_code": "CM"})
    assert response.status_code == 400 and "déjà pris" in response.text
    assert paul(db_session).nickname == "Paul"


def test_invalid_nickname_is_refused(client):
    register(client)
    assert client.post("/profile", data={"nickname": "a b", "country_code": "CM"}).status_code == 400


def test_week_shows_matchday_when_known(client, db_session):
    register(client)
    match = add_pick(db_session, paul(db_session), (1, 0), (1, 0), hours_ago=0)
    match.matchday = 12
    db_session.commit()
    assert "Journée 12" in client.get("/profile?period=week").text


# --- Page publique (« Partager mes stats ») ---

def test_public_stats_page_without_account(client, db_session):
    register(client)
    add_pick(db_session, paul(db_session), (2, 1), (2, 1))
    logout(client)
    page = client.get("/players/1").text
    assert "<h1>Paul</h1>" in page and "100 %" in page
    assert "Répartition des pronos" in page and "de mes pronos" not in page
    assert 'content="5 pts · 100 % de réussite' in page  # aperçu WhatsApp
    assert 'href="/register"' in page and "Jouer à MaxitProno" in page
    assert 'href="/profile/edit"' not in page and "Prochain :" not in page


def test_public_stats_page_offers_the_league(client, db_session):
    register(client)
    _, code = create_league(client)
    assert f"/players/1?league={code}" in client.get("/profile").text  # lien partagé
    logout(client)
    page = client.get(f"/players/1?league={code}").text
    assert f'href="/join/{code}?ref=1"' in page and "Rejoindre la ligue « Bureau Casa »" in page


def test_public_stats_page_ignores_a_league_of_someone_else(client):
    register(client)
    _, code = create_league(client)
    logout(client)
    register(client, "Awa")
    assert "/join/" not in client.get(f"/players/2?league={code}").text


def test_public_stats_unknown_player(client):
    assert client.get("/players/999").status_code == 404


def test_remontada_badge_from_rank_history(client, db_session):
    """6 joueurs devant Paul le 1er jour, il en double 5 le lendemain."""
    from app.jobs.score_predictions import score_finished_matches
    from app.services.scoring import ScoringRules
    from tests.test_leaderboard_page import add_player
    register(client)
    day1 = add_match(db_session, -48, status=MatchStatus.FINISHED, score=(1, 0))
    day2 = add_match(db_session, -24, status=MatchStatus.FINISHED, score=(4, 4))
    rivals = [add_player(db_session, name) for name in ("Ali", "Bea", "Cyr", "Dan", "Eva", "Fred")]
    for rival in rivals:
        db_session.add(Prediction(user_id=rival.id, match_id=day1.id, home_score=2, away_score=0))
    db_session.add(Prediction(user_id=rivals[0].id, match_id=day2.id, home_score=4, away_score=4))
    db_session.add(Prediction(user_id=paul(db_session).id, match_id=day1.id, home_score=0, away_score=1))
    db_session.add(Prediction(user_id=paul(db_session).id, match_id=day2.id, home_score=4, away_score=4))
    db_session.commit()
    score_finished_matches(db_session, ScoringRules(), utc_now())
    page = client.get("/profile").text
    assert page.count('class="unlocked"') == 1  # Remontada : 7e -> 2e
