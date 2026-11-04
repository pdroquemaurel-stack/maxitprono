from datetime import UTC, date, datetime, timedelta

from app.jobs.import_matches import import_matches, import_upcoming_matches, update_live_scores
from app.models import Competition, Match
from app.models.match import MatchStatus
from tests.fixture_factory import fixture_item


class FakeClient:
    """Remplace ApiFootballClient : renvoie des réponses prévues et note les appels."""

    def __init__(self, fixtures=None):
        self.fixtures = fixtures or {}  # api_id de compétition -> liste d'éléments
        self.calls = []

    def get_fixtures(self, league, season, date_from, date_to):
        self.calls.append(("fixtures", league, season, date_from, date_to))
        return self.fixtures.get(league, [])



def add_competition(db, api_id=61, active=True, season=2026):
    competition = Competition(api_id=api_id, name=f"Comp {api_id}", season=season, is_active=active)
    db.add(competition)
    db.commit()
    return competition


def test_import_creates_matches_for_active_competitions_only(db):
    add_competition(db, 61, active=True)
    add_competition(db, 39, active=False)
    client = FakeClient(fixtures={61: [fixture_item(1), fixture_item(2)], 39: [fixture_item(3)]})

    count = import_matches(db, client, date(2026, 11, 1), date(2026, 11, 15))

    assert count == 2
    assert db.query(Match).count() == 2
    assert client.calls == [("fixtures", 61, 2026, "2026-11-01", "2026-11-15")]


def test_import_can_force_season(db):
    add_competition(db, 61, season=2026)
    client = FakeClient()
    import_matches(db, client, date(2024, 8, 16), date(2024, 8, 31), season=2024)
    assert client.calls[0][2] == 2024


def test_reimport_updates_postponed_match_without_duplicate(db):
    add_competition(db, 61)
    import_matches(db, FakeClient(fixtures={61: [fixture_item(1)]}), date(2024, 8, 1), date(2024, 8, 31))

    postponed = fixture_item(1, date="2024-09-20T18:00:00+00:00", status="PST")
    import_matches(db, FakeClient(fixtures={61: [postponed]}), date(2024, 8, 1), date(2024, 9, 30))

    match = db.query(Match).one()
    assert match.status == MatchStatus.POSTPONED
    assert match.kickoff_at == datetime(2024, 9, 20, 18, 0, tzinfo=UTC)
    assert match.synced_at is not None


def test_import_upcoming_uses_window_from_d_minus_3_to_d_plus_14(db):
    add_competition(db, 61)
    client = FakeClient()
    import_upcoming_matches(db, client, date(2026, 11, 4))
    assert client.calls[0][3:] == ("2026-11-01", "2026-11-18")


def add_match(db, competition, api_id, kickoff_at, status=MatchStatus.SCHEDULED):
    db.add(Match(api_id=api_id, competition=competition, season=2024, home_team="A",
                 away_team="B", kickoff_at=kickoff_at, status=status))
    db.commit()


NOW = datetime(2026, 11, 10, 20, 0, tzinfo=UTC)


def test_update_live_scores_makes_no_call_when_no_match_in_progress(db):
    competition = add_competition(db)
    add_match(db, competition, 1, NOW + timedelta(hours=2))  # pas commencé
    add_match(db, competition, 2, NOW - timedelta(hours=1), MatchStatus.FINISHED)
    client = FakeClient()

    assert update_live_scores(db, client, NOW) == 0
    assert client.calls == []


def test_update_live_scores_updates_started_match_using_its_season(db):
    competition = add_competition(db, season=2026)
    add_match(db, competition, 1, NOW - timedelta(minutes=50))
    live = fixture_item(1, date="2026-11-10T19:10:00+00:00", status="2H", goals=(2, 1))
    client = FakeClient(fixtures={61: [live]})

    assert update_live_scores(db, client, NOW) == 1

    assert client.calls == [("fixtures", 61, 2024, "2026-11-10", "2026-11-10")]
    match = db.query(Match).one()
    assert (match.status, match.home_score, match.away_score) == (MatchStatus.LIVE, 2, 1)


def test_update_live_scores_ignores_other_matches_of_the_day(db):
    competition = add_competition(db)
    add_match(db, competition, 1, NOW - timedelta(minutes=30))
    other = fixture_item(99, date="2026-11-10T12:00:00+00:00", status="FT", goals=(0, 0))
    client = FakeClient(fixtures={61: [fixture_item(1, status="1H", goals=(0, 1)), other]})

    update_live_scores(db, client, NOW)

    assert db.query(Match).count() == 1


def test_update_live_scores_makes_one_call_per_competition_and_day(db):
    ligue1, premier_league = add_competition(db, 61), add_competition(db, 39)
    for api_id in (1, 2, 3):
        add_match(db, ligue1, api_id, NOW - timedelta(minutes=30))
    add_match(db, premier_league, 4, NOW - timedelta(minutes=30))
    client = FakeClient(fixtures={
        61: [fixture_item(i, status="1H") for i in (1, 2, 3)],
        39: [fixture_item(4, status="1H", league=39)],
    })

    assert update_live_scores(db, client, NOW) == 4
    assert sorted(call[1] for call in client.calls) == [39, 61]
