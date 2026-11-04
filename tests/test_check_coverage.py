from app.models import Competition
from scripts.check_coverage import save_competition, summarize_league

LEAGUE_ITEM = {
    "league": {"id": 2, "name": "UEFA Champions League", "type": "Cup", "logo": "https://x/2.png"},
    "country": {"name": "World"},
    "seasons": [
        {"year": 2025, "current": False, "coverage": {}},
        {"year": 2026, "current": True, "start": "2026-07-01", "end": "2027-05-29",
         "coverage": {"fixtures": {"events": True}, "predictions": True, "odds": False}},
    ],
}


def test_summarize_league_uses_current_season():
    s = summarize_league(LEAGUE_ITEM)
    assert (s["api_id"], s["season"], s["is_current"]) == (2, 2026, True)
    assert (s["events"], s["predictions"], s["odds"]) == (True, True, False)


def test_summarize_league_without_current_season_takes_last():
    item = {**LEAGUE_ITEM, "seasons": [{"year": 2023}, {"year": 2024}]}
    s = summarize_league(item)
    assert (s["season"], s["is_current"], s["predictions"]) == (2024, False, False)


def test_save_competition_keeps_activation(db):
    db.add(Competition(api_id=2, name="Old name", is_active=True))
    db.commit()
    save_competition(db, summarize_league(LEAGUE_ITEM))
    db.commit()
    competition = db.query(Competition).one()
    assert competition.name == "UEFA Champions League"
    assert competition.season == 2026
    assert competition.is_active is True
