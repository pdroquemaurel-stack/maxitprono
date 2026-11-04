"""Vérifie la couverture API-Football des compétitions visées par le POC.

Usage : python -m scripts.check_coverage

Coût : environ 10 appels. Les compétitions trouvées sont enregistrées
en base (inactives), pour pouvoir les activer ensuite sans nouvel appel.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import Competition
from app.providers.api_football import ApiFootballError, make_client

# Identifiants API-Football connus ; le nom renvoyé par l'API est affiché pour contrôle
LEAGUES_BY_ID = {
    "CAN": 6,
    "Ligue des champions CAF": 12,
    "Ligue des champions UEFA": 2,
    "Premier League": 39,
    "Liga": 140,
    "Ligue 1": 61,
    "Serie A": 135,
    "Bundesliga": 78,
}
# Championnats locaux : identifiants inconnus, on cherche par pays
LOCAL_COUNTRIES = ["Cameroon", "Burkina-Faso"]


def summarize_league(item: dict) -> dict:
    """Résumé d'une compétition renvoyée par /leagues : dernière saison et couverture."""
    seasons = item.get("seasons") or []
    current = next((s for s in seasons if s.get("current")), seasons[-1] if seasons else {})
    coverage = current.get("coverage") or {}
    return {
        "api_id": item["league"]["id"],
        "name": item["league"]["name"],
        "type": item["league"].get("type", ""),
        "country": item["country"]["name"],
        "logo_url": item["league"].get("logo") or "",
        "season": current.get("year"),
        "is_current": bool(current.get("current")),
        "start": current.get("start", ""),
        "end": current.get("end", ""),
        "events": bool((coverage.get("fixtures") or {}).get("events")),
        "predictions": bool(coverage.get("predictions")),
        "odds": bool(coverage.get("odds")),
    }


def save_competition(db: Session, summary: dict) -> None:
    """Crée ou met à jour la compétition, sans toucher à son activation."""
    competition = db.scalar(select(Competition).where(Competition.api_id == summary["api_id"]))
    if competition is None:
        competition = Competition(api_id=summary["api_id"], is_active=False)
        db.add(competition)
    competition.name = summary["name"]
    competition.country = summary["country"]
    competition.logo_url = summary["logo_url"]
    competition.season = summary["season"]


def yes_no(value: bool) -> str:
    return "oui" if value else "non"


def print_row(label: str, s: dict) -> None:
    season = f"{s['season']}{'' if s['is_current'] else ' (pas en cours)'}"
    print(f"{label:<26} | {s['api_id']:>5} | {s['name'][:28]:<28} | {s['country'][:13]:<13} | "
          f"{season:<18} | {s['start']} → {s['end']} | événements {yes_no(s['events']):<3} | "
          f"pronos {yes_no(s['predictions']):<3} | cotes {yes_no(s['odds'])}")


def main() -> None:
    db = SessionLocal()
    client = make_client(db)
    try:
        for label, league_id in LEAGUES_BY_ID.items():
            items = client.get_leagues(id=league_id)
            if not items:
                print(f"{label:<26} | introuvable (id {league_id})")
                continue
            summary = summarize_league(items[0])
            save_competition(db, summary)
            print_row(label, summary)

        for country in LOCAL_COUNTRIES:
            items = client.get_leagues(country=country)
            if not items:
                print(f"{country:<26} | aucune compétition couverte")
            for item in items:
                summary = summarize_league(item)
                save_competition(db, summary)
                print_row(country, summary)
        db.commit()
    except ApiFootballError as exc:
        print(f"Arrêt : {exc}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
