# MaxitProno — État des lieux

Mis à jour le 4 novembre 2026 (dernier commit : `d3a010b`, 34 commits sur `main`).

## 1. Avancement des étapes (SPEC §12)

| # | Étape | État | Fichiers concernés |
|---|-------|------|--------------------|
| 1 | Squelette, config, base, accueil, déploiement Render | **Fait** | `app/main.py`, `app/config.py`, `app/db.py`, `render.yaml`, `alembic.ini`, `migrations/` |
| 2 | Client API-Football, import compétitions/matchs, script de couverture | **Fait** | `app/providers/api_football.py`, `app/jobs/import_matches.py`, `app/services/fixtures.py`, `scripts/check_coverage.py`, `scripts/run_import.py`, `scripts/activate_competition.py` |
| 3 | Comptes joueurs (pseudo + PIN, profil, règlement) | **Fait** | `app/auth/` (`pin_auth.py`, `session.py`), `app/services/accounts.py`, `app/services/avatars.py`, `app/routes/accounts.py`, templates `register/login/profile/rules` |
| 4 | Pronostics + clôture 10 min | **Fait** | `app/models/prediction.py`, `app/services/deadlines.py`, `app/services/predictions.py`, `app/routes/matches.py`, `matches.html`, `_match_card.html` |
| 5 | Points + classements + départage | **Fait** | `app/services/scoring.py`, `app/services/ranking.py`, `app/services/leaderboards.py`, `app/jobs/score_predictions.py`, `app/routes/leaderboard.py`, `app/routes/results.py` |
| 6 | Ligues privées + lien de partage | **À faire** | Emplacements réservés dans `home.html` (sélecteur de ligue) et `result.html` (pronos de la ligue) ; aucune table `leagues` |
| 7 | Pourcentages 1/N/2 | **À faire** | Emplacement réservé dans `_match_card.html` ; aucun champ en base |
| 8 | Back-office admin + KPIs | **À faire** | Remplacé provisoirement par `scripts/activate_competition.py` ; barème figé dans `ScoringRules()` |
| 9 | Traductions FR/EN, page d'erreur, finitions mobile | **Partiel** | `app/i18n/fr.json` et `en.json` complets (133 clés chacun, mêmes clés) ; mais la langue est figée sur `DEFAULT_LANGUAGE` (`app/templating.py`), pas de choix par le joueur ; pas de page « erreur réseau + réessayer » (`_error.html` n'est qu'un message de formulaire) |

Hors découpage : `scripts/seed_demo.py` (données de démo sans API) ; gestion du fuseau horaire du joueur (`app/services/timezones.py`, `static/js/timezone.js`, cookie `tz`).

## 2. Fournisseur de données

- **Un seul client** : `ApiFootballClient` (`app/providers/api_football.py`), méthodes `get_status`, `get_leagues`, `get_fixtures`. Chaque appel est journalisé dans `api_call_logs` (endpoint, paramètres, code HTTP, quota restant, erreur), avec commit immédiat.
- **Appels** : uniquement via les scripts manuels (`check_coverage`, `run_import`, `run_import --scores`). Aucune tâche planifiée, aucune route de déclenchement.
- **Dépendances directes à API-Football dans le reste de l'app** :
  - `app/jobs/import_matches.py` importe et type `ApiFootballClient`, lit `item["fixture"]["id"]` (format brut API-Football).
  - `app/services/fixtures.py` : `parse_fixture` et la table des statuts `_STATUS_BY_CODE` sont propres au format API-Football.
  - `scripts/check_coverage.py` : identifiants de ligues API-Football en dur, `summarize_league` au format API-Football.
  - Modèles : `Competition.api_id` (unique) et `Match.api_id` (unique) = identifiants API-Football, sans colonne « fournisseur ».
  - `scripts/seed_demo.py` : compétition démo repérée par `api_id = 999999`.
  - `app/config.py` ne lit que `API_FOOTBALL_KEY`.
- **Pas de table « équipes »** : noms et logos sont stockés à plat dans `matches` (`home_team`, `home_logo_url`…).
- Les pages, services de classement et pronostics ne dépendent **pas** du fournisseur (ils ne lisent que `matches`).

## 3. Déploiement

- `render.yaml` : base Postgres `maxitprono-db` (free, Francfort) + web service Python ; démarrage = `alembic upgrade head && uvicorn …` ; `healthCheckPath: /health`.
- Variables déclarées : `PYTHON_VERSION`, `DATABASE_URL` (depuis la base), `SECRET_KEY` (générée), `DEFAULT_LANGUAGE`, `SECURE_COOKIES`, `API_FOOTBALL_KEY` (sync: false).
- **Modification non commitée** de `render.yaml` : ajoute déjà `DATA_PROVIDER`, `FOOTBALL_DATA_API_KEY` et `SYNC_TOKEN` (sync: false), alors que le code ne les lit pas encore.
- `.env.example` : `API_FOOTBALL_KEY`, `DATABASE_URL`, `SECRET_KEY`, `DEFAULT_LANGUAGE`, `SECURE_COOKIES`.
- `.env` local (noms seulement) : `DATA_PROVIDER`, `FOOTBALL_DATA_API_KEY`, `API_FOOTBALL_KEY`.
- **Tâches planifiées : aucune.** APScheduler n'est pas dans `requirements.txt` et n'est pas utilisé. Pas de dossier `.github/workflows/`.

## 4. Charte DESIGN.md

Socle en place (`app/static/css/style.css`) : variables de couleur, polices Outfit et DM Sans (hébergées localement, pas via Google Fonts — plus léger), cartes sans ombre, badges, code couleur des scores (`score_colors.py` + `score-colors.js`), barre de navigation à 5 onglets.

| Écran | État |
|-------|------|
| Accueil (Ma ligue) | **Partiel** : podium et carte « matchs sans prono » conformes ; manquent sélecteur de ligue, fil d'activité, bouton d'invitation WhatsApp (dépendent de l'étape 6) |
| Pronos (saisie directe) | **Conforme** : cases de score colorées, état « Ferme dans… », bouton collé en bas ; manquent la ligne 1/N/2 (étape 7) et les écussons |
| Match clôturé | **Partiel** : carte score final et bandeau du prono conformes ; manquent les pronos des membres de la ligue (étape 6) |
| Classements | **Conforme** (liste, onglets pleine largeur) ; onglet « ligue » absent |
| Résultats | Conforme au style général (pas de maquette dédiée) |
| Profil, connexion, inscription, règles | Composants de base (cartes, formulaires, boutons) ; pas de maquette dédiée |

Écussons d'équipes : URL stockées en base mais **jamais affichées** (ni logo, ni initiales de repli).

## 5. Tests

`pytest` (via `.venv`) : **224 tests passent, 0 échec**, 1 avertissement (dépréciation `httpx` dans le TestClient de Starlette).

## 6. Incohérences et dettes

1. **Version de Python** : `.python-version` et `render.yaml` visent 3.12, mais le `.venv` local tourne en Python 3.14.
2. **`render.yaml` modifié sans le code correspondant** (voir §3).
3. **Aucune planification** alors que la SPEC §10 prévoit l'import quotidien et les scores toutes les 5-10 min ; CLAUDE.md mentionne APScheduler, absent des dépendances.
4. **Couplage à API-Football** dans les jobs, `fixtures.py` et les modèles (`api_id` sans fournisseur) — voir §2.
5. **Pas de table équipes** : logos dupliqués à chaque match, pas d'identifiant d'équipe.
6. **Langue non sélectionnable** par le joueur (§1, étape 9).
7. **Barème de points** codé en dur (`ScoringRules()` par défaut) en attendant le back-office.
8. **Compétition démo** identifiée par un faux `api_id` (999999) : fragile si un second fournisseur réutilise cette plage.
9. `README.md` ne parle que d'API-Football et de la saisie de `API_FOOTBALL_KEY`.
10. Avertissement de dépréciation `httpx` / `starlette.testclient` (sans effet aujourd'hui).
