"""Fabrique d'éléments /fixtures au format de l'API-Football."""


def fixture_item(api_id=1001, date="2024-08-16T19:00:00+00:00", status="NS",
                 home="Le Havre", away="PSG", goals=(None, None), league=61, season=2024):
    return {
        "fixture": {"id": api_id, "date": date, "status": {"short": status, "long": ""}},
        "league": {"id": league, "season": season, "round": "Regular Season - 1"},
        "teams": {
            "home": {"id": 1, "name": home, "logo": f"https://x/{home}.png"},
            "away": {"id": 2, "name": away, "logo": f"https://x/{away}.png"},
        },
        "goals": {"home": goals[0], "away": goals[1]},
        "score": {"fulltime": {"home": goals[0], "away": goals[1]}},
    }
