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
