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
2. Saisir `API_FOOTBALL_KEY` quand Render la demande.
3. Valider : Render crée la base, installe, applique les migrations et démarre l'app.

Vérification : `https://<nom-du-service>.onrender.com/health` doit répondre `{"status":"ok"}`.

## Données foot (API-Football)

```bash
python -m scripts.check_coverage              # couverture des compétitions (~10 appels)
python -m scripts.activate_competition 61     # activer une compétition (ici Ligue 1)
python -m scripts.run_import                  # import des matchs J-3 à J+14
python -m scripts.run_import --scores         # mise à jour des matchs en cours
# Offre gratuite (saisons 2022-2024 uniquement) :
python -m scripts.run_import --season 2024 --from 2024-08-16 --to 2024-08-31
```

## Données de démo (tests sans l'API)

```bash
python -m scripts.seed_demo            # matchs à venir + joueurs fictifs (PIN 0000) + classements
python -m scripts.seed_demo --finish   # termine les matchs démo ouverts et calcule les points
python -m scripts.seed_demo --reset    # supprime les données démo
```
