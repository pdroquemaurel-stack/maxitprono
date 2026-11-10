import json
from datetime import UTC, date, datetime

import httpx
import pytest

from app.models import ApiCallLog
from app.models.match import MatchStatus
from app.providers.football_data import (BASE_URL, FootballDataClient, FootballDataError,
                                         final_score, map_match_status, parse_competition,
                                         parse_match)


def match_item(match_id=497410, status="TIMED", full_time=(None, None), duration="REGULAR",
               penalties=None, utc_date="2026-11-08T20:45:00Z"):
    """Élément de la réponse /competitions/{code}/matches (format v4, réduit)."""
    score = {"winner": None, "duration": duration,
             "fullTime": {"home": full_time[0], "away": full_time[1]}}
    if penalties:
        score["penalties"] = {"home": penalties[0], "away": penalties[1]}
    return {
        "id": match_id, "utcDate": utc_date, "status": status, "matchday": 12,
        "season": {"id": 2316, "startDate": "2026-08-15", "endDate": "2027-05-22"},
        "homeTeam": {"id": 524, "name": "Paris Saint-Germain FC", "shortName": "PSG",
                     "tla": "PSG", "crest": "https://crests.football-data.org/524.png"},
        "awayTeam": {"id": 516, "name": "Olympique de Marseille", "shortName": "Marseille",
                     "tla": "MAR", "crest": "https://crests.football-data.org/516.png"},
        "score": score,
    }


COMPETITION_ITEM = {
    "id": 2015, "area": {"name": "France"}, "name": "Ligue 1", "code": "FL1",
    "type": "LEAGUE", "emblem": "https://crests.football-data.org/FL1.png", "plan": "TIER_ONE",
    "currentSeason": {"id": 2316, "startDate": "2026-08-15", "endDate": "2027-05-22"},
}


def make_client(db, handler):
    http = httpx.Client(base_url=BASE_URL, transport=httpx.MockTransport(handler))
    return FootballDataClient("test-key", db, http=http)


def ok_response(payload, available="9"):
    return httpx.Response(200, json=payload, headers={"X-Requests-Available-Minute": available})


# --- Appels ---

def test_get_matches_sends_key_and_params_and_converts(db):
    seen = {}

    def handler(request):
        seen["key"] = request.headers["X-Auth-Token"]
        seen["path"] = request.url.path
        seen["params"] = dict(request.url.params)
        return ok_response({"matches": [match_item()]})

    matches = make_client(db, handler).get_matches("FL1", 2026, date(2026, 11, 1), date(2026, 11, 15))

    assert seen["key"] == "test-key"
    assert seen["path"] == "/v4/competitions/FL1/matches"
    assert seen["params"] == {"dateFrom": "2026-11-01", "dateTo": "2026-11-15", "season": "2026"}
    assert [m["external_id"] for m in matches] == ["497410"]


def test_get_matches_without_season(db):
    seen = {}

    def handler(request):
        seen["params"] = dict(request.url.params)
        return ok_response({"matches": []})

    make_client(db, handler).get_matches("FL1", None, date(2026, 11, 1), date(2026, 11, 1))
    assert "season" not in seen["params"]


def test_list_competitions_keeps_poc_competitions_only(db):
    other = {**COMPETITION_ITEM, "code": "DED", "name": "Eredivisie"}
    payload = {"competitions": [COMPETITION_ITEM, other]}
    competitions = make_client(db, lambda r: ok_response(payload)).list_competitions()
    assert [c["external_id"] for c in competitions] == ["FL1"]


def test_successful_call_is_logged_with_remaining_calls_per_minute(db):
    make_client(db, lambda r: ok_response({"competitions": []}, available="7")).list_competitions()

    log = db.query(ApiCallLog).one()
    assert (log.provider, log.endpoint, log.status_code) == ("football_data", "competitions", 200)
    assert json.loads(log.params) == {}
    assert log.requests_remaining == 7
    assert log.error == ""


def test_http_error_raises_with_message_and_is_logged(db):
    def handler(request):
        return httpx.Response(429, json={"message": "You reached your request limit."})

    with pytest.raises(FootballDataError, match="HTTP 429 You reached"):
        make_client(db, handler).list_competitions()
    assert db.query(ApiCallLog).one().status_code == 429


def test_network_error_raises_and_is_logged(db):
    def handler(request):
        raise httpx.ConnectError("timeout")

    with pytest.raises(FootballDataError, match="injoignable"):
        make_client(db, handler).list_competitions()
    assert db.query(ApiCallLog).one().status_code is None


def test_missing_key_is_refused(db):
    with pytest.raises(FootballDataError, match="manquante"):
        FootballDataClient("", db)


# --- Conversion des réponses ---

@pytest.mark.parametrize("code, expected", [
    ("SCHEDULED", MatchStatus.SCHEDULED), ("TIMED", MatchStatus.SCHEDULED),
    ("IN_PLAY", MatchStatus.LIVE), ("PAUSED", MatchStatus.LIVE), ("SUSPENDED", MatchStatus.LIVE),
    ("FINISHED", MatchStatus.FINISHED), ("AWARDED", MatchStatus.FINISHED),
    ("POSTPONED", MatchStatus.POSTPONED), ("CANCELLED", MatchStatus.CANCELLED),
    ("XYZ", MatchStatus.SCHEDULED),
])
def test_map_match_status(code, expected):
    assert map_match_status(code) == expected


def test_parse_scheduled_match():
    fields = parse_match(match_item())
    assert (fields["provider"], fields["external_id"], fields["season"]) == ("football_data", "497410", 2026)
    assert fields["kickoff_at"] == datetime(2026, 11, 8, 20, 45, tzinfo=UTC)
    assert fields["status"] == MatchStatus.SCHEDULED
    assert (fields["home_team"], fields["away_team"]) == ("PSG", "Marseille")
    assert fields["home_logo_url"] == "https://crests.football-data.org/524.png"
    assert (fields["home_score"], fields["away_score"]) == (None, None)


def test_parse_match_uses_full_name_without_short_name():
    item = match_item()
    item["homeTeam"]["shortName"] = None
    assert parse_match(item)["home_team"] == "Paris Saint-Germain FC"


def test_parse_finished_match():
    fields = parse_match(match_item(status="FINISHED", full_time=(3, 1)))
    assert (fields["status"], fields["home_score"], fields["away_score"]) == (MatchStatus.FINISHED, 3, 1)


def test_final_score_removes_penalty_shootout():
    # 1-1 après prolongations, 4-3 aux tirs au but : fullTime vaut 5-4
    score = match_item(full_time=(5, 4), duration="PENALTY_SHOOTOUT", penalties=(4, 3))["score"]
    assert final_score(score) == (1, 1)


def test_final_score_keeps_extra_time_goals():
    score = match_item(full_time=(2, 1), duration="EXTRA_TIME")["score"]
    assert final_score(score) == (2, 1)


def test_parse_competition():
    s = parse_competition(COMPETITION_ITEM)
    assert (s["external_id"], s["name"], s["country"]) == ("FL1", "Ligue 1", "France")
    assert (s["season"], s["is_current"]) == (2026, True)
    assert (s["start"], s["end"]) == ("2026-08-15", "2027-05-22")


def test_parse_competition_without_current_season():
    s = parse_competition({**COMPETITION_ITEM, "currentSeason": None})
    assert (s["season"], s["is_current"]) == (None, False)


def test_get_probabilities_makes_no_call(db):
    def handler(request):
        raise AssertionError("aucun appel attendu")

    assert make_client(db, handler).get_probabilities("497410") is None
    assert db.query(ApiCallLog).count() == 0


def test_parse_match_keeps_matchday():
    assert parse_match(match_item())["matchday"] == 12
    knockout = match_item() | {"matchday": None}  # phase à élimination directe
    assert parse_match(knockout)["matchday"] is None


def test_parse_match_minute_when_given():
    """Offre gratuite : pas de champ « minute », le match reste « En direct » sans minute."""
    assert parse_match(match_item(status="IN_PLAY"))["minute"] is None
    assert parse_match({**match_item(status="IN_PLAY"), "minute": 54})["minute"] == 54
    assert parse_match({**match_item(status="IN_PLAY"), "minute": "54"})["minute"] == 54
    assert parse_match({**match_item(status="PAUSED"), "minute": 45})["minute"] is None
    assert parse_match({**match_item(status="FINISHED"), "minute": 90})["minute"] is None
