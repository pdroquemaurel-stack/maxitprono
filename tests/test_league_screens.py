"""Refonte des écrans Ligues (lot 1) : liste, détail, création, invitation."""
from datetime import timedelta

from app.models import Competition, League, LeagueMember, User
from app.models.match import MatchStatus
from app.models.types import utc_now
from tests.test_league_pages import create_league, logout, register
from tests.test_match_pages import add_match, db_session  # noqa: F401
from tests.test_result_league_picks import add_prediction


def login(client, nickname):
    logout(client)
    client.post("/login", data={"nickname": nickname, "pin": "1234"})


def league_with_members(client, names, league_name="Bureau Casa"):
    """Paul crée la ligue, les autres la rejoignent ; Paul est connecté à la fin."""
    register(client)
    league_id, code = create_league(client, league_name)
    for name in names:
        logout(client)
        register(client, name)
        client.post(f"/join/{code}")
    login(client, "Paul")
    return league_id, code


def backdate_members(db, days=30):
    """Arrivée dans la ligue antidatée : les matchs déjà joués comptent au classement."""
    for member in db.query(LeagueMember):
        member.joined_at = utc_now() - timedelta(days=days)
    db.commit()


# --- Écran 1 : mes ligues ---

def test_player_without_league_sees_empty_state_and_both_actions(client):
    register(client)
    page = client.get("/leagues").text
    assert "Pas encore de ligue" in page
    assert 'href="/leagues/new"' in page and 'action="/leagues/join"' in page
    assert "Code ex. BDL-7K2" in page
    assert "pronos à faire" not in page and "prono à faire" not in page  # aucun match ouvert
    assert "Mes ligues privées" not in page


def test_reminder_card_counts_open_matches_without_prediction(client, db_session):
    register(client)
    add_match(db_session, 5, home="Lions", away="Étalons")
    add_match(db_session, 30, home="Aigles", away="Éléphants")
    page = client.get("/leagues").text
    assert "2 pronos à faire" in page
    assert "Premier match : Lions – Étalons, ferme dans" in page
    assert 'class="lg-reminder-link" href="/matches"' in page


def test_league_card_shows_rank_move_faces_and_activity(client, db_session):
    league_id, _ = league_with_members(client, ["Awa", "Kevin", "Sarah", "Moussa"])
    backdate_members(db_session)
    old = add_match(db_session, -72, status=MatchStatus.FINISHED, score=(1, 0))
    add_prediction(db_session, "Awa", old, 1, 0, 5, exact=True)
    add_prediction(db_session, "Paul", old, 2, 0, 3)
    last = add_match(db_session, -3, status=MatchStatus.FINISHED, score=(2, 2))
    add_prediction(db_session, "Paul", last, 2, 2, 5, exact=True)  # Paul passe devant Awa
    add_prediction(db_session, "Awa", last, 0, 1, 0)

    page = client.get("/leagues").text
    assert "Mes ligues privées (1)" in page
    assert "5 membres · Toutes compétitions" in page
    assert "<strong>1er</strong>" in page and 'class="lg-move up"' in page
    assert "+2" in page  # 3 avatars sur 5 membres
    assert "Toi\n" in page or "Toi " in page  # ma dernière activité : score exact
    assert f'href="/leagues/{league_id}"' in page


def test_typed_code_errors_are_explained(client, db_session):
    _, code = league_with_members(client, [])
    response = client.post("/leagues/join", data={"code": code})  # Paul est déjà membre
    assert response.status_code == 400 and "Tu es déjà dans cette ligue" in response.text
    assert "Aucune ligue" in client.post("/leagues/join", data={"code": "ZZZ-ZZZ"}).text

    from app.models import GameSettings
    db_session.add(GameSettings(id=1, winner_points=3, exact_bonus=2, league_max_members=1,
                                prediction_days_ahead=7, updated_at=utc_now()))
    db_session.commit()
    logout(client)
    register(client, "Awa")
    response = client.post("/leagues/join", data={"code": code[:3] + "-" + code[3:]})
    assert response.status_code == 400 and "complète" in response.text


# --- Écran 2 : détail d'une ligue ---

def test_single_member_league_has_no_broken_podium(client):
    league_id, _ = league_with_members(client, [])
    page = client.get(f"/leagues/{league_id}").text
    assert "Le classement démarre au premier match terminé" in page
    assert "lg-step-2" not in page and "lg-rows" not in page
    assert "Joueur de la semaine" not in page


def test_single_ranked_member_gets_a_one_step_podium(client, db_session):
    league_id, _ = league_with_members(client, [])
    backdate_members(db_session)
    match = add_match(db_session, -3, status=MatchStatus.FINISHED, score=(1, 0))
    add_prediction(db_session, "Paul", match, 1, 0, 5, exact=True)
    page = client.get(f"/leagues/{league_id}").text
    assert "lg-step-1" in page and "lg-step-2" not in page and "lg-step-3" not in page
    assert "Joueur de la semaine" in page and "Lanterne rouge" not in page  # seul : pas de lanterne
    assert "En tête" in page  # écart avec le 1er


def test_podium_order_list_from_4th_and_week_cards(client, db_session):
    names = ["Awa", "Kevin", "Sarah", "Moussa"]
    league_id, _ = league_with_members(client, names)
    backdate_members(db_session)
    match = add_match(db_session, -3, status=MatchStatus.FINISHED, score=(1, 0))
    for name, points in zip(["Awa", "Kevin", "Sarah", "Moussa", "Paul"], [5, 3, 3, 0, 0]):
        add_prediction(db_session, name, match, 1, 0, points, exact=points == 5)

    page = client.get(f"/leagues/{league_id}").text
    podium = page[page.index('class="lg-podium"'):page.index("</ol>")]
    assert podium.index("lg-step-2") < podium.index("lg-step-1") < podium.index("lg-step-3")
    assert "Awa" in podium
    rows = page[page.index('class="lg-card lg-rows"'):]
    assert 'class="lg-row me"' in rows  # ma ligne surlignée
    assert "Joueur de la semaine" in page and "Lanterne rouge" in page


def test_big_league_shows_a_preview_then_all_members(client, db_session):
    names = [f"Joueur{i:02d}" for i in range(24)]  # 25 membres avec Paul
    league_id, _ = league_with_members(client, names)
    backdate_members(db_session)
    match = add_match(db_session, -3, status=MatchStatus.FINISHED, score=(1, 0))
    for i, name in enumerate(names):
        add_prediction(db_session, name, match, 1, 0, 5 if i < 12 else 3, exact=i < 12)
    add_prediction(db_session, "Paul", match, 0, 2, 0)  # Paul dernier, hors de l'aperçu

    page = client.get(f"/leagues/{league_id}").text
    assert "Voir les 25 membres" in page
    assert page.count('<li class="lg-row') == 7 + 1  # aperçu + ma ligne
    assert 'class="lg-row me"' in page
    full = client.get(f"/leagues/{league_id}?tab=ranking&all=1").text
    assert full.count('<li class="lg-row') == 22 and "Voir les 25 membres" not in full


def test_next_match_shows_who_played_and_trend_never_scores(client, db_session):
    league_id, _ = league_with_members(client, ["Awa", "Kevin"])
    match = add_match(db_session, 5, home="Lions", away="Étalons")
    add_prediction(db_session, "Awa", match, 7, 3, 0)  # 0 point : pas encore calculé ici
    add_prediction(db_session, "Kevin", match, 4, 4, 0)

    page = client.get(f"/leagues/{league_id}").text
    card = page[page.index("lg-next"):page.index('id="tabs"')]
    assert "Lions" in card and "Ferme dans" in card and "data-deadline" in card
    assert "2 / 3 ont joué" in card and "pronos révélés au coup d&#39;envoi" in card
    assert "50 %" in card  # domicile 50 %, nul 50 %
    for score in (">7<", ">3<", ">4<"):
        assert score not in card  # aucun score des autres avant le coup d'envoi
    assert "Faire mon prono" in card


def test_matches_tab_with_no_prediction_at_all(client, db_session):
    league_id, _ = league_with_members(client, ["Awa"])
    add_match(db_session, -3, status=MatchStatus.FINISHED, score=(2, 1))
    page = client.get(f"/leagues/{league_id}?tab=matches").text
    assert "Les pronos de la ligue" in page
    assert page.count("pas de prono") == 2
    assert "0 scores exacts dans la ligue sur ce match." in page


def test_matches_tab_points_pills_and_never_an_upcoming_match(client, db_session):
    league_id, _ = league_with_members(client, ["Awa", "Kevin"])
    finished = add_match(db_session, -3, status=MatchStatus.FINISHED, score=(2, 1))
    add_prediction(db_session, "Paul", finished, 1, 0, 3)
    add_prediction(db_session, "Awa", finished, 2, 1, 5, exact=True)
    add_prediction(db_session, "Kevin", finished, 0, 2, 0)
    upcoming = add_match(db_session, 5, home="Aigles", away="Éléphants")

    page = client.get(f"/leagues/{league_id}?tab=matches").text
    assert 'class="lg-pts exact">+5' in page and 'class="lg-pts good">+3' in page
    assert 'class="lg-pts miss">0' in page
    assert "1 score exact dans la ligue sur ce match." in page
    # Un match pas encore joué ne peut pas être choisi
    forced = client.get(f"/leagues/{league_id}?tab=matches&match={upcoming.id}").text
    assert "Aigles – Éléphants ·" not in forced and "lg-final" in forced


def test_menu_keeps_owner_and_member_actions(client):
    league_id, code = league_with_members(client, ["Awa"])
    page = client.get(f"/leagues/{league_id}").text
    assert "Réglages de la ligue" in page and "Retirer un membre" in page
    assert "Supprimer la ligue" in page and "Quitter la ligue" not in page
    login(client, "Awa")
    page = client.get(f"/leagues/{league_id}").text
    assert "Quitter la ligue" in page and "Supprimer la ligue" not in page
    assert "Créée par Paul" in page


# --- Écran 3 : créer une ligue ---

def test_create_page_lists_colors_competitions_and_scoring(client, db_session):
    register(client)
    db_session.add(Competition(provider="api_football", external_id="61", name="Ligue 1",
                               is_active=True))
    db_session.commit()
    page = client.get("/leagues/new").text
    assert page.count('name="color"') == 4 and 'value="orange" checked' in page
    assert "Ligue 1" in page and 'value="all" checked' in page
    assert "Classique (conseillé)" in page and "5 pts score exact, 3 pts bon résultat" in page
    assert "Expert" not in page and "Créer ma ligue" in page


def test_create_with_color_and_competitions_then_ready_screen(client, db_session):
    register(client)
    ligue1 = add_match(db_session, -3, status=MatchStatus.FINISHED, score=(1, 0), name="Ligue 1")
    other = add_match(db_session, -2, status=MatchStatus.FINISHED, score=(1, 0), name="Premier League")
    league_id, code = create_league(client, "Les Lions", color="green",
                                    competitions=[str(ligue1.competition_id)])
    league = db_session.get(League, league_id)
    db_session.refresh(league)
    assert league.color == "green"

    ready = client.get(f"/leagues/{league_id}/ready").text
    assert "Ta ligue est prête" in ready and f"/j/{code}?ref=1" in ready
    assert "Copier le lien" in ready and "Aller à ma ligue" in ready

    backdate_members(db_session)
    add_prediction(db_session, "Paul", ligue1, 1, 0, 5, exact=True)
    add_prediction(db_session, "Paul", other, 1, 0, 5, exact=True)  # hors compétitions de la ligue
    page = client.get(f"/leagues/{league_id}").text
    assert "lg-color-green" in page and "Ligue 1 ·" in page
    assert '<span class="lg-podium-points">5 pts</span>' in page


def test_create_rejects_a_too_long_name(client):
    register(client)
    response = client.post("/leagues", data={"name": "x" * 31})
    assert response.status_code == 400 and "entre 3 et 30 caractères" in response.text


def test_owner_edits_settings_and_member_cannot(client):
    league_id, _ = league_with_members(client, ["Awa"])
    response = client.post(f"/leagues/{league_id}/settings",
                           data={"name": "Nouveau nom", "color": "peach"}, follow_redirects=False)
    assert response.headers["location"] == f"/leagues/{league_id}/settings?saved=1"
    assert "Nouveau nom" in client.get(f"/leagues/{league_id}").text
    login(client, "Awa")
    settings = client.get(f"/leagues/{league_id}/settings").text
    assert 'name="name"' not in settings and "Quitter la ligue" in settings
    response = client.post(f"/leagues/{league_id}/settings", data={"name": "Pirate"})
    assert response.status_code == 403


# --- Lien d'invitation ---

def test_short_link_redirects_and_keeps_inviter(client):
    _, code = league_with_members(client, [])
    response = client.get(f"/j/{code}?ref=1", follow_redirects=False)
    assert response.headers["location"] == f"/join/{code}?ref=1"


def test_login_from_invite_link_joins_the_league(client, db_session):
    league_id, code = league_with_members(client, [])
    logout(client)
    register(client, "Awa")
    logout(client)
    response = client.post("/login", data={"nickname": "Awa", "pin": "1234",
                                           "next": f"/join/{code}?ref=1"}, follow_redirects=False)
    assert response.headers["location"] == f"/leagues/{league_id}?joined=1"
    awa = db_session.query(User).filter_by(nickname="Awa").one()
    member = db_session.query(LeagueMember).filter_by(user_id=awa.id).one()
    assert member.invited_by_id == 1


def test_ma_ligue_tab_is_active_on_league_screens(client):
    league_id, _ = league_with_members(client, [])
    for url in ("/leagues", f"/leagues/{league_id}", "/leagues/new"):
        page = client.get(url).text
        assert 'href="/" class="active" aria-current="page"' in page
