# MaxitProno — instructions pour Claude Code

## Le projet
MaxitProno est un jeu de pronostics football gratuit (style "pronos entre amis").
Le POC tourne d'abord comme site web mobile autonome, testé sur téléphone.
Ensuite, il sera intégré dans la super app Max it (Orange) comme mini app TCMPP
au format **web-view** : le site doit donc rester un site web classique.

La spécification fonctionnelle complète est dans `docs/SPEC.md`. La lire avant toute tâche.

## Règles de code (importantes)
- Code **simple et lisible** avant tout. Pas d'optimisation prématurée, pas d'abstraction inutile.
- Fonctions courtes, noms explicites en anglais, commentaires en français si utile.
- Pas de nouveau framework ou de nouvelle dépendance sans me demander.
- Toute la logique métier (calcul des points, clôture des pronostics, départage)
  est dans `app/services/`, en fonctions pures testées.
- Ne jamais appeler l'API foot depuis le navigateur : uniquement depuis le back-end, avec cache en base.
- Jamais de clé ou de secret dans le code : tout passe par les variables d'environnement (`.env`).

## Stack
- Python 3.12, FastAPI, SQLAlchemy 2, Alembic (migrations)
- PostgreSQL (SQLite accepté en local)
- Pages rendues côté serveur avec Jinja2 + un peu de JavaScript natif (pas de React)
- CSS simple, mobile-first, page légère (réseaux 3G)
- Tâches planifiées : APScheduler dans le process de l'app (suffisant pour le POC)
- Tests : pytest
- Données foot : API-Football (https://www.api-football.com), clé dans `API_FOOTBALL_KEY`
- Hébergement POC : Render (web service) + Postgres managé

## Structure attendue
```
app/
  main.py            # création de l'app FastAPI, routes montées
  config.py          # lecture des variables d'environnement
  db.py              # session SQLAlchemy
  models/            # tables
  routes/            # pages joueur + back-office admin
  services/          # logique métier pure (scoring, ranking, deadlines)
  providers/         # client API-Football (seul endroit qui appelle l'API)
  auth/              # authentification, interchangeable (POC puis Max it)
  templates/         # Jinja2
  static/            # css, js, images
tests/
docs/SPEC.md
```

## Authentification
Prévoir une interface d'auth interchangeable dans `app/auth/` :
- POC : pseudo + code PIN à 4 chiffres (ou lien magique), session par cookie.
- Plus tard : login Max it via `wx.login` (code temporaire -> back-end -> identifiant crypté unique).
Le reste de l'app ne dépend que d'un `user_id` interne, jamais du mode de login.

## Commandes
- Installer : `pip install -r requirements.txt`
- Lancer en local : `uvicorn app.main:app --reload`
- Tests : `pytest`
- Migration : `alembic revision --autogenerate -m "..."` puis `alembic upgrade head`

## Façon de travailler
- Avant une fonctionnalité non triviale : proposer un plan court, attendre mon accord.
- Une fonctionnalité à la fois, avec ses tests, puis un commit clair.
- Lancer `pytest` avant de dire qu'une tâche est terminée.
- Textes de l'interface en français et en anglais (fichiers de traduction simples), français par défaut.
- Heures des matchs affichées dans le fuseau horaire local du joueur.
