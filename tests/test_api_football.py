import json
from datetime import UTC, date, datetime

import httpx
import pytest

from app.models import ApiCallLog
from app.models.match import MatchStatus
from app.providers.api_football import (BASE_URL, ApiFootballClient, ApiFootballError,
                                        map_fixture_status, parse_fixture, parse_league)
from tests.fixture_factory import fixture_item


def make_client(db, handler):
    http = httpx.Client(base_url=BASE_URL, transport=httpx.MockTransport(handler))
    return ApiFootballClient("test-key", db, http=http)


def ok_response(payload, remaining="95"):
    body = {"errors": [], "response": payload}
    return httpx.Response(200, json=body, headers={"x-ratelimit-requests-remaining": remaining})


def test_get_fixtures_sends_key_and_params(db):
    seen = {}

    def handler(request):
        seen["key"] = request.headers["x-apisports-key"]
        seen["path"] = request.url.path
        seen["params"] = dict(request.url.params)
        return ok_response([{"fixture": {"id": 1}}])

    result = make_client(db, handler).get_fixtures(2, 2026, "2026-11-04", "2026-11-18")

    assert result == [{"fixture": {"id": 1}}]
    assert seen["key"] == "test-key"
    assert seen["path"] == "/fixtures"
    assert seen["params"] == {"league": "2", "season": "2026", "from": "2026-11-04", "to": "2026-11-18"}


def test_get_matches_converts_fixtures_and_can_omit_season(db):
    seen = {}

    def handler(request):
        seen["params"] = dict(request.url.params)
        return ok_response([fixture_item(7, status="FT", goals=(2, 0))])

    matches = make_client(db, handler).get_matches("61", None, date(2026, 11, 4), date(2026, 11, 5))

    assert seen["params"] == {"league": "61", "from": "2026-11-04", "to": "2026-11-05"}
    assert [(m["external_id"], m["home_score"], m["away_score"]) for m in matches] == [("7", 2, 0)]


def test_successful_call_is_logged_with_remaining_quota(db):
    make_client(db, lambda r: ok_response([], remaining="42")).get_leagues(country="Cameroon")

    log = db.query(ApiCallLog).one()
    assert log.endpoint == "leagues"
    assert json.loads(log.params) == {"country": "Cameroon"}
    assert log.status_code == 200
    assert log.requests_remaining == 42
    assert log.error == ""


def test_api_errors_field_raises_and_is_logged(db):
    def handler(request):
        return httpx.Response(200, json={"errors": {"token": "Invalid API key"}, "response": []})

    with pytest.raises(ApiFootballError, match="Invalid API key"):
        make_client(db, handler).get_status()
    assert "Invalid API key" in db.query(ApiCallLog).one().error


def test_http_error_raises(db):
    with pytest.raises(ApiFootballError, match="HTTP 500"):
        make_client(db, lambda r: httpx.Response(500, text="oops")).get_status()


def test_network_error_raises_and_is_logged(db):
    def handler(request):
        raise httpx.ConnectError("timeout")

    with pytest.raises(ApiFootballError, match="injoignable"):
        make_client(db, handler).get_status()
    assert db.query(ApiCallLog).one().status_code is None


def test_missing_key_is_refused(db):
    with pytest.raises(ApiFootballError, match="manquante"):
        ApiFootballClient("", db)


def test_call_log_records_provider(db):
    make_client(db, lambda r: ok_response([])).get_status()
    assert db.query(ApiCallLog).one().provider == "api_football"


# --- Conversion des réponses ---

@pytest.mark.parametrize("code, expected", [
    ("NS", MatchStatus.SCHEDULED), ("TBD", MatchStatus.SCHEDULED),
    ("1H", MatchStatus.LIVE), ("HT", MatchStatus.LIVE), ("P", MatchStatus.LIVE),
    ("FT", MatchStatus.FINISHED), ("AET", MatchStatus.FINISHED), ("PEN", MatchStatus.FINISHED),
    ("PST", MatchStatus.POSTPONED),
    ("CANC", MatchStatus.CANCELLED), ("ABD", MatchStatus.CANCELLED),
    ("XYZ", MatchStatus.SCHEDULED),
])
def test_map_fixture_status(code, expected):
    assert map_fixture_status(code) == expected


def test_parse_fixture_finished_match():
    fields = parse_fixture(fixture_item(status="FT", goals=(1, 4)))
    assert (fields["provider"], fields["external_id"]) == ("api_football", "1001")
    assert fields["season"] == 2024
    assert fields["kickoff_at"] == datetime(2024, 8, 16, 19, 0, tzinfo=UTC)
    assert fields["status"] == MatchStatus.FINISHED
    assert (fields["home_team"], fields["away_team"]) == ("Le Havre", "PSG")
    assert (fields["home_score"], fields["away_score"]) == (1, 4)


def test_parse_fixture_keeps_timezone():
    fields = parse_fixture(fixture_item(date="2024-08-16T21:00:00+02:00"))
    assert fields["kickoff_at"] == datetime(2024, 8, 16, 19, 0, tzinfo=UTC)


LEAGUE_ITEM = {
    "league": {"id": 2, "name": "UEFA Champions League", "type": "Cup", "logo": "https://x/2.png"},
    "country": {"name": "World"},
    "seasons": [
        {"year": 2025, "current": False, "coverage": {}},
        {"year": 2026, "current": True, "start": "2026-07-01", "end": "2027-05-29",
         "coverage": {"fixtures": {"events": True}, "predictions": True, "odds": False}},
    ],
}


def test_parse_league_uses_current_season():
    s = parse_league(LEAGUE_ITEM)
    assert (s["external_id"], s["season"], s["is_current"]) == ("2", 2026, True)
    assert s["coverage"] == "événements oui · pronos oui · cotes non"


def test_parse_league_without_current_season_takes_last():
    s = parse_league({**LEAGUE_ITEM, "seasons": [{"year": 2023}, {"year": 2024}]})
    assert (s["season"], s["is_current"]) == (2024, False)
    assert "pronos non" in s["coverage"]
