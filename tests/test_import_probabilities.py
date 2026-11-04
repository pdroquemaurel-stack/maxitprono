from datetime import UTC, datetime, timedelta

from app.jobs.import_probabilities import MAX_CALLS, import_probabilities
from app.models import Competition, Match
from app.models.match import MatchStatus

NOW = datetime(2026, 11, 4, 12, 0, tzinfo=UTC)


class FakeProvider:
    name = "api_football"

    def __init__(self, values=(50, 30, 20)):
        self.values = values
        self.calls = []

    def get_probabilities(self, match_id):
        self.calls.append(match_id)
        return self.values


def add_match(db, external_id, hours, provider="api_football", status=MatchStatus.SCHEDULED,
              probs=(None, None, None)):
    competition = db.query(Competition).first() or Competition(
        provider="api_football", external_id="61", name="Ligue 1")
    match = Match(provider=provider, external_id=external_id, competition=competition,
                  home_team="A", away_team="B", kickoff_at=NOW + timedelta(hours=hours),
                  status=status, prob_home=probs[0], prob_draw=probs[1], prob_away=probs[2])
    db.add(match)
    db.commit()
    return match


def test_fills_upcoming_matches_within_three_days(db):
    soon = add_match(db, "1", 24)
    later = add_match(db, "2", 24 * 4)
    provider = FakeProvider()

    assert import_probabilities(db, provider, NOW) == 1

    assert provider.calls == ["1"]
    assert (soon.prob_home, soon.prob_draw, soon.prob_away) == (50, 30, 20)
    assert later.prob_home is None


def test_skips_matches_already_filled_started_or_from_other_providers(db):
    add_match(db, "1", 24, probs=(40, 30, 30))
    add_match(db, "2", -1)
    add_match(db, "3", 24, status=MatchStatus.POSTPONED)
    add_match(db, "4", 24, provider="football_data")
    provider = FakeProvider()

    assert import_probabilities(db, provider, NOW) == 0
    assert provider.calls == []


def test_provider_without_probabilities_leaves_match_empty(db):
    match = add_match(db, "1", 24)
    assert import_probabilities(db, FakeProvider(values=None), NOW) == 0
    assert match.prob_home is None


def test_calls_are_capped(db):
    for i in range(MAX_CALLS + 5):
        add_match(db, str(i), 1 + i)
    provider = FakeProvider()
    import_probabilities(db, provider, NOW)
    assert len(provider.calls) == MAX_CALLS
