import json

import httpx
import pytest

from app.models import ApiCallLog
from app.providers.api_football import BASE_URL, ApiFootballClient, ApiFootballError


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


def test_fixtures_by_ids_joins_ids_with_dashes(db):
    seen = {}

    def handler(request):
        seen["ids"] = request.url.params["ids"]
        return ok_response([])

    make_client(db, handler).get_fixtures_by_ids([10, 11, 12])
    assert seen["ids"] == "10-11-12"


def test_fixtures_by_ids_refuses_more_than_20(db):
    with pytest.raises(ValueError):
        make_client(db, lambda r: ok_response([])).get_fixtures_by_ids(list(range(21)))


def test_missing_key_is_refused(db):
    with pytest.raises(ApiFootballError, match="manquante"):
        ApiFootballClient("", db)
