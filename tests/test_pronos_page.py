"""Page Pronos : calendrier des jours, filtres compétition × statut, états des matchs, visiteur."""
import re
from dataclasses import replace
from datetime import UTC, datetime

import pytest

from app.models import Prediction
from app.models.match import MatchStatus
from app.services.settings_store import get_settings, save_settings
from tests.test_match_pages import add_match, db_session, login, predict  # noqa: F401

# Heure figée : le 10 juin 2030 à 7 h à Douala (fuseau par défaut, UTC+1). Les matchs à
# quelques heures d'ici tombent donc « aujourd'hui », le jour affiché par défaut.
NOW = datetime(2030, 6, 10, 6, 0, tzinfo=UTC)


@pytest.fixture(autouse=True)
def frozen_now(monkeypatch):
    monkeypatch.setattr("app.routes.matches.utc_now", lambda: NOW)
    monkeypatch.setattr("tests.test_match_pages.utc_now", lambda: NOW)


def visible_cards(page: str) -> list[str]:
    """Identifiants des lignes de match affichées (sans l'attribut hidden)."""
    cards = re.findall(r'<article class="card match-card" id="(m\d+)"([^>]*)>', page)
    return [card_id for card_id, attributes in cards if " hidden" not in attributes]


def pill_count(page: str, key: str) -> int:
    pill = re.search(rf'data-comp-key="{key}".*?data-count>(\d+)<', page, re.S)
    return int(pill.group(1))


def setup_matches(client, db):
    """Aujourd'hui. Ligue 1 : un match à jouer et un pronostiqué ;
    Premier League : un à jouer et un en direct."""
    l1_todo = add_match(db, 2, home="Lions", name="Ligue 1")
    l1_done = add_match(db, 4, home="Aigles", name="Ligue 1")
    pl_todo = add_match(db, 6, home="Arsenal", name="Premier League")
    pl_live = add_match(db, -1, home="Chelsea", name="Premier League", status=MatchStatus.LIVE,
                        score=(1, 0))
    login(client)
    predict(client, l1_done, "2", "0")
    user_id = db.query(Prediction).one().user_id
    db.add(Prediction(user_id=user_id, match_id=pl_live.id, home_score=2, away_score=1))
    db.commit()
    return l1_todo, l1_done, pl_todo, pl_live


def test_default_is_all_competitions_and_to_play(client, db_session):
    l1_todo, _, pl_todo, _ = setup_matches(client, db_session)
    page = client.get("/matches").text
    assert visible_cards(page) == [f"m{l1_todo.id}", f"m{pl_todo.id}"]
    assert re.search(r'class="pr-comp active" href="\?day=2030-06-10&comp=all', page)
    assert re.search(r'data-status-key="todo" class="active"', page)


def test_competition_pills_built_from_matches(client, db_session):
    setup_matches(client, db_session)
    page = client.get("/matches").text
    assert re.findall(r'data-comp-key="(\w+)"', page) == ["all", "l1", "pl"]
    assert pill_count(page, "all") == 2 and pill_count(page, "l1") == 1 and pill_count(page, "pl") == 1


def test_competition_filter_alone(client, db_session):
    l1_todo, _, _, _ = setup_matches(client, db_session)
    page = client.get("/matches?comp=l1").text
    assert visible_cards(page) == [f"m{l1_todo.id}"]


def test_status_mine_keeps_editable_and_live(client, db_session):
    _, l1_done, _, pl_live = setup_matches(client, db_session)
    page = client.get("/matches?status=mine").text
    assert visible_cards(page) == [f"m{pl_live.id}", f"m{l1_done.id}"]
    # Compteurs recalculés selon le statut
    assert pill_count(page, "all") == 2 and pill_count(page, "l1") == 1 and pill_count(page, "pl") == 1


def test_filters_combined(client, db_session):
    _, _, _, pl_live = setup_matches(client, db_session)
    page = client.get("/matches?comp=pl&status=mine").text
    assert visible_cards(page) == [f"m{pl_live.id}"]


def test_all_competitions_and_all_statuses(client, db_session):
    setup_matches(client, db_session)
    page = client.get("/matches?comp=all&status=all").text
    assert len(visible_cards(page)) == 4
    assert pill_count(page, "all") == 4
    assert 'data-empty hidden' in page


def test_unknown_filters_fall_back_to_defaults(client, db_session):
    l1_todo, _, pl_todo, _ = setup_matches(client, db_session)
    page = client.get("/matches?comp=xyz&status=bad").text
    assert visible_cards(page) == [f"m{l1_todo.id}", f"m{pl_todo.id}"]


def test_hidden_matches_stay_in_page_with_their_inputs(client, db_session):
    """Un filtre masque les lignes sans les retirer : les scores saisis restent et partent avec « Valider »."""
    _, l1_done, pl_todo, _ = setup_matches(client, db_session)
    page = client.get("/matches?comp=l1&status=mine").text
    assert f'name="home_{pl_todo.id}"' in page  # masqué mais présent
    assert f'name="home_{l1_done.id}"' in page and 'value="2"' in page


def test_empty_state_for_filters_without_match(client, db_session):
    add_match(db_session, 20, name="Ligue 1")
    login(client)
    page = client.get("/matches?status=mine").text
    assert visible_cards(page) == []
    assert "Aucun match ici" in page and "Change de compétition ou de statut." in page
    assert 'data-empty hidden' not in page


def test_day_with_single_match_and_counts(client, db_session):
    login(client)  # page privée : joueur connecté
    add_match(db_session, 2)
    page = client.get("/matches").text
    assert "1 match<" in page
    assert re.search(r'class="pr-day-title">Aujourd&#39;hui · ', page)


# --- Calendrier des jours ---

def day_links(page: str) -> list[str]:
    return re.findall(r'class="pr-day-link[^"]*" href="\?day=([\d-]+)', page)


def test_calendar_shows_admin_day_count_from_today(client, db_session):
    login(client)
    page = client.get("/matches").text
    days = day_links(page)
    assert len(days) == get_settings(db_session).prediction_days_ahead
    assert days[0] == "2030-06-10"
    assert re.search(r'class="pr-day-link active" href="\?day=2030-06-10', page)


def test_calendar_follows_admin_setting(client, db_session):
    save_settings(db_session, replace(get_settings(db_session), prediction_days_ahead=3), NOW)
    login(client)
    assert day_links(client.get("/matches").text) == ["2030-06-10", "2030-06-11", "2030-06-12"]


def test_only_selected_day_is_shown(client, db_session):
    today = add_match(db_session, 2, home="Lions")
    tomorrow = add_match(db_session, 26, home="Aigles")
    login(client)
    assert visible_cards(client.get("/matches").text) == [f"m{today.id}"]
    page = client.get("/matches?day=2030-06-11").text
    assert visible_cards(page) == [f"m{tomorrow.id}"]
    assert f'name="home_{today.id}"' in page  # masqué mais présent : sa saisie part avec « Valider »
    assert re.search(r'class="pr-day-link active" href="\?day=2030-06-11', page)
    assert pill_count(page, "all") == 1  # compteurs du jour choisi


def test_unknown_day_falls_back_to_today(client, db_session):
    match = add_match(db_session, 2)
    login(client)
    for day in ("2031-01-01", "pas-une-date"):
        assert visible_cards(client.get(f"/matches?day={day}").text) == [f"m{match.id}"]


def test_day_without_match(client, db_session):
    add_match(db_session, 2)
    login(client)
    page = client.get("/matches?day=2030-06-12").text
    assert visible_cards(page) == []
    assert "Aucun match ce jour-là" in page and 'data-empty hidden' not in page


def test_dot_on_days_with_matches_to_play(client, db_session):
    add_match(db_session, 26)  # demain, sans prono
    login(client)
    page = client.get("/matches").text
    links = re.findall(r'href="\?day=([\d-]+)[^"]*".*?class="pr-dot( off)?"', page, re.S)
    assert dict(links)["2030-06-11"] == "" and dict(links)["2030-06-10"] == " off"


def test_save_bar_counts_all_days(client, db_session):
    add_match(db_session, 2)
    add_match(db_session, 26)
    login(client)
    assert "2 pronos à faire" in client.get("/matches").text


def test_matches_after_last_calendar_day_are_left_out(client, db_session):
    save_settings(db_session, replace(get_settings(db_session), prediction_days_ahead=2), NOW)
    late = add_match(db_session, 42, home="Aigles")  # 12/06 à 1 h à Douala : 3e jour
    login(client)
    assert f'id="m{late.id}"' not in client.get("/matches?status=all").text


def test_live_match_shows_real_score_and_my_pick(client, db_session):
    _, _, _, pl_live = setup_matches(client, db_session)
    page = client.get("/matches?status=all").text
    card = page.split(f'id="m{pl_live.id}"')[1].split("</article>")[0]
    assert "En direct" in card and "1 – 0" in card and "Ton prono 2 : 1" in card
    assert "<input" not in card


def test_finished_match_without_prediction(client, db_session):
    add_match(db_session, -2, status=MatchStatus.FINISHED, score=(2, 0))
    login(client)
    page = client.get("/matches?status=all").text
    assert "Terminé" in page and "Pas de prono" in page and "lg-pts" not in page


def test_finished_match_with_points(client, db_session):
    match = add_match(db_session, 24)
    login(client)
    predict(client, match, "2", "0")
    prediction = db_session.query(Prediction).one()
    match.status, match.home_score, match.away_score = MatchStatus.FINISHED, 2, 0
    prediction.points, prediction.is_exact, prediction.is_winner = 5, True, True
    db_session.commit()
    page = client.get("/matches?status=all").text
    assert '<span class="lg-pts exact">+5</span>' in page


def test_cancelled_match_has_no_input(client, db_session):
    match = add_match(db_session, 24, status=MatchStatus.CANCELLED)
    login(client)
    page = client.get("/matches?status=all").text
    assert "Annulé" in page and f'name="home_{match.id}"' not in page


def test_missing_logo_falls_back_to_initials(client, db_session):
    login(client)  # page privée : joueur connecté
    add_match(db_session, 20, home="Paris Saint-Germain", away="Marseille")
    page = client.get("/matches").text
    assert '<span class="crest-initials">PSG</span>' in page
    assert "<img src=" not in page  # ni logo d'équipe ni emblème de compétition
    assert '<span class="pr-emblem-code">L1</span>' in page


def test_inputs_have_hidden_labels(client, db_session):
    match = add_match(db_session, 20, home="Paris Saint-Germain")
    login(client)
    page = client.get("/matches").text
    assert f'<label class="visually-hidden" for="s{match.id}h">Buts Paris Saint-Germain</label>' in page


def test_save_bar_counts_matches_without_prediction(client, db_session):
    setup_matches(client, db_session)
    page = client.get("/matches").text
    assert "2 pronos à faire" in page and "2 à faire" in page
    assert "Modifiable jusqu&#39;à 10 min avant" in page


def test_prediction_on_match_started_meanwhile_is_refused(client, db_session):
    match = add_match(db_session, 20)
    login(client)
    match.kickoff_at = match.kickoff_at.replace(year=2000)  # coup d'envoi passé entre-temps
    db_session.commit()
    response = predict(client, match)
    assert response.status_code == 400 and "Trop tard" in response.json()["error"]


def test_tabbar_has_pronos_active(client, db_session):
    login(client)  # page privée : joueur connecté
    page = client.get("/matches").text
    assert '<a href="/matches" class="active" aria-current="page">' in page


def test_english_texts(client, db_session):
    login(client)  # page privée : joueur connecté
    add_match(db_session, 20)
    client.cookies.set("lang", "en")
    page = client.get("/matches").text
    assert "To play" in page and "My picks" in page and ">All<" in page


def test_live_pill_shows_minute_when_known(client, db_session):
    login(client)  # page privée : joueur connecté
    match = add_match(db_session, -1, status=MatchStatus.LIVE, score=(1, 0))
    page = client.get("/matches?status=all").text
    assert ">En direct</span>" in page  # minute inconnue
    match.minute = 54
    db_session.commit()
    page = client.get("/matches?status=all").text
    assert "En direct · 54&#39;" in page
    client.cookies.set("lang", "en")
    assert "Live · 54&#39;" in client.get("/matches?status=all").text
