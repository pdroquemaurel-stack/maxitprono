# MaxitProno

Jeu de pronostics football gratuit (POC web mobile). Spécification : `docs/SPEC.md`.

## En local

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # puis renseigner les valeurs
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

Tests : `pytest`

## Déploiement sur Render

Le fichier `render.yaml` décrit la base Postgres et le web service.

1. Sur render.com : **New → Blueprint**, choisir le dépôt `maxitprono`.
2. Saisir `FOOTBALL_DATA_API_KEY` (et `API_FOOTBALL_KEY` si `DATA_PROVIDER=api_football`) quand Render les demande.
3. Valider : Render crée la base, installe, applique les migrations et démarre l'app.

Vérification : `https://<nom-du-service>.onrender.com/health` doit répondre `{"status":"ok"}`.

## Données foot

Le fournisseur est choisi par `DATA_PROVIDER` :
- `football_data` (défaut, POC) : [football-data.org](https://www.football-data.org), clé `FOOTBALL_DATA_API_KEY`.
  Offre gratuite : grands championnats européens et Ligue des champions, 10 appels par minute.
- `api_football` : [API-Football](https://www.api-football.com), clé `API_FOOTBALL_KEY`.

Les identifiants de compétition sont ceux du fournisseur (codes `FL1`, `PL`, `CL`…
chez football-data.org ; numéros `61`, `39`, `2`… chez API-Football).

```bash
python -m scripts.check_coverage              # compétitions du POC couvertes (enregistrées inactives)
python -m scripts.activate_competition FL1    # activer une compétition (ici Ligue 1)
python -m scripts.run_import                  # import des matchs J-3 à J+14
python -m scripts.run_import --scores         # mise à jour des matchs en cours
python -m scripts.run_import --season 2024 --from 2024-08-16 --to 2024-08-31
```

Changement de fournisseur : modifier `DATA_PROVIDER`, puis

```bash
python -m scripts.reset_football_data         # simulation : liste ce qui serait supprimé
python -m scripts.reset_football_data --yes   # supprime les données de l'ancien fournisseur
                                              # (pronos compris, joueurs et démo conservés)
                                              # puis enregistre les compétitions du nouveau
```

## Données de démo (tests sans l'API)

```bash
python -m scripts.seed_demo            # matchs à venir + joueurs fictifs (PIN 0000) + classements
python -m scripts.seed_demo --finish   # termine les matchs démo ouverts et calcule les points
python -m scripts.seed_demo --reset    # supprime les données démo
```
