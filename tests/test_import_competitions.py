from app.jobs.import_competitions import import_competitions, save_competition
from app.models import Competition


def summary(external_id="FL1", name="Ligue 1", season=2026):
    return {"external_id": external_id, "name": name, "country": "France", "logo_url": "",
            "season": season, "is_current": True, "start": "", "end": "", "coverage": ""}


class FakeProvider:
    name = "football_data"

    def list_competitions(self):
        return [summary("FL1"), summary("PL", "Premier League")]


def test_import_competitions_creates_them_inactive(db):
    import_competitions(db, FakeProvider())
    competitions = db.query(Competition).order_by(Competition.external_id).all()
    assert [(c.provider, c.external_id, c.is_active) for c in competitions] == [
        ("football_data", "FL1", False), ("football_data", "PL", False)]


def test_save_competition_keeps_activation(db):
    db.add(Competition(provider="football_data", external_id="FL1", name="Old", is_active=True))
    db.commit()
    save_competition(db, "football_data", summary(season=2027))
    db.commit()
    competition = db.query(Competition).one()
    assert (competition.name, competition.season, competition.is_active) == ("Ligue 1", 2027, True)


def test_same_code_from_another_provider_is_a_new_competition(db):
    db.add(Competition(provider="api_football", external_id="FL1", name="Autre"))
    db.commit()
    save_competition(db, "football_data", summary())
    db.commit()
    assert db.query(Competition).count() == 2
