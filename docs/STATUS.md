# MaxitProno — État des lieux

Mis à jour le 4 novembre 2026, après la PARTIE 2 étape 3 (synchronisation par `/internal/sync` + GitHub Action).

## 1. Avancement des étapes (SPEC §12)

| # | Étape | État | Fichiers concernés |
|---|-------|------|--------------------|
| 1 | Squelette, config, base, accueil, déploiement Render | **Fait** | `app/main.py`, `app/config.py`, `app/db.py`, `render.yaml`, `alembic.ini`, `migrations/` |
| 2 | Clients fournisseurs (football-data.org, API-Football), import compétitions/matchs, script de couverture | **Fait** | `app/providers/` (`base.py`, `football_data.py`, `api_football.py`), `app/jobs/import_competitions.py`, `app/jobs/import_matches.py`, `scripts/check_coverage.py`, `scripts/run_import.py`, `scripts/activate_competition.py`, `scripts/reset_football_data.py` |
| 3 | Comptes joueurs (pseudo + PIN, profil, règlement) | **Fait** | `app/auth/` (`pin_auth.py`, `session.py`), `app/services/accounts.py`, `app/services/avatars.py`, `app/routes/accounts.py`, templates `register/login/profile/rules` |
| 4 | Pronostics + clôture 10 min | **Fait** | `app/models/prediction.py`, `app/services/deadlines.py`, `app/services/predictions.py`, `app/routes/matches.py`, `matches.html`, `_match_card.html` |
| 5 | Points + classements + départage | **Fait** | `app/services/scoring.py`, `app/services/ranking.py`, `app/services/leaderboards.py`, `app/jobs/score_predictions.py`, `app/routes/leaderboard.py`, `app/routes/results.py` |
| 6 | Ligues privées + lien de partage | **À faire** | Emplacements réservés dans `home.html` (sélecteur de ligue) et `result.html` (pronos de la ligue) ; aucune table `leagues` |
| 7 | Pourcentages 1/N/2 | **À faire** | Emplacement réservé dans `_match_card.html` ; aucun champ en base |
| 8 | Back-office admin + KPIs | **À faire** | Remplacé provisoirement par `scripts/activate_competition.py` ; barème figé dans `ScoringRules()` |
| 9 | Traductions FR/EN, page d'erreur, finitions mobile | **Partiel** | `app/i18n/fr.json` et `en.json` complets (133 clés chacun, mêmes clés) ; mais la langue est figée sur `DEFAULT_LANGUAGE` (`app/templating.py`), pas de choix par le joueur ; pas de page « erreur réseau + réessayer » (`_error.html` n'est qu'un message de formulaire) |

Hors découpage : `scripts/seed_demo.py` (données de démo sans API) ; gestion du fuseau horaire du joueur (`app/services/timezones.py`, `static/js/timezone.js`, cookie `tz`).

## 2. Fournisseurs de données

- **Choix par `DATA_PROVIDER`** (`app/providers/__init__.py`, `make_provider`) : `football_data` (défaut, POC) ou `api_football`.
- **Interface** `FootballProvider` (`app/providers/base.py`) : `list_competitions()` et `get_matches(...)`, qui renvoient des dictionnaires déjà à notre format. La conversion des réponses (statuts, scores, logos) est propre à chaque client ; le reste de l'app ne voit jamais le format brut.
- **football-data.org** (`FootballDataClient`) : API v4, en-tête `X-Auth-Token`, 1 appel pour la liste des compétitions, 1 par compétition et par période pour les matchs. Compétitions du POC : `CL`, `PL`, `PD`, `FL1`, `SA`, `BL1` (pas de CAN, CAF, Elite One ni Burkina sur l'offre gratuite). Tirs au but retirés du score final. Vérifié sur l'API réelle le 4 novembre 2026.
- **API-Football** (`ApiFootballClient`) : inchangé côté appels, conversion déplacée dans le module du client.
- **Journal** `api_call_logs` : une ligne par appel avec le fournisseur, l'endpoint, les paramètres, le code HTTP, le quota restant (par jour chez API-Football, par minute chez football-data) et l'erreur.
- **Identifiants** : `provider` + `external_id` (texte) sur `competitions` et `matches`, uniques ensemble. Les imports ne touchent que les données du fournisseur actif. Compétition démo : `provider = "demo"`.
- **Pas de table « équipes »** (choix assumé pour le POC) : noms et logos stockés à plat dans `matches`.
- **Changement de fournisseur** : `scripts/reset_football_data.py`. Simulation par défaut ; avec `--yes`, supprime les compétitions des autres fournisseurs, leurs matchs (y compris ceux ajoutés à la main) et les pronostics sur ces matchs, puis enregistre les compétitions du fournisseur actif (inactives). Joueurs, journal des appels et démo conservés (démo supprimée avec `--include-demo`). La base locale contient encore 12 compétitions API-Football (22 matchs, 0 prono) : le script n'a été lancé qu'en simulation.
- **Synchronisation automatique** : `POST /internal/sync?task=fixtures|scores` (`app/routes/internal.py`), protégée par `Authorization: Bearer <SYNC_TOKEN>` (401 si jeton faux, 503 si `SYNC_TOKEN` vide, 502 avec le message si le fournisseur échoue). Points calculés après chaque passage. Appelée par `.github/workflows/sync.yml` : `fixtures` à 04:00 UTC, `scores` toutes les 10 min (aucun appel API sans match en cours), plus un lancement manuel. Testée en local de bout en bout le 4 novembre 2026 (14 matchs de Ligue 1 importés).
- **En local** : scripts manuels (`check_coverage`, `run_import`, `run_import --scores`).

## 3. Déploiement

- `render.yaml` : base Postgres `maxitprono-db` (free, Francfort) + web service Python ; démarrage = `alembic upgrade head && uvicorn …` ; `healthCheckPath: /health`.
- Variables déclarées : `PYTHON_VERSION`, `DATABASE_URL` (depuis la base), `SECRET_KEY` (générée), `DEFAULT_LANGUAGE`, `SECURE_COOKIES`, `API_FOOTBALL_KEY` (sync: false).
- `render.yaml` déclare aussi `DATA_PROVIDER` (football_data), `FOOTBALL_DATA_API_KEY` et `SYNC_TOKEN` (sync: false, à saisir dans Render).
- GitHub Actions : secret `SYNC_TOKEN` et variable `APP_URL` à configurer (voir README).
- `.env.example` : `DATA_PROVIDER`, `FOOTBALL_DATA_API_KEY`, `API_FOOTBALL_KEY`, `DATABASE_URL`, `SECRET_KEY`, `DEFAULT_LANGUAGE`, `SECURE_COOKIES`, `SYNC_TOKEN`.
- `.env` local (noms seulement) : `DATA_PROVIDER`, `FOOTBALL_DATA_API_KEY`, `API_FOOTBALL_KEY`.
- **Tâches planifiées** : GitHub Action `.github/workflows/sync.yml` (pas de planificateur dans l'app). GitHub peut retarder les tâches de quelques minutes et les suspend après 60 jours sans commit.

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

`pytest` (via `.venv`, **Python 3.12.3**) : **278 tests passent, 0 échec**, 1 avertissement (dépréciation `httpx` dans le TestClient de Starlette).

## 6. Incohérences et dettes

1. **Langue non sélectionnable** par le joueur (§1, étape 9).
2. **Barème de points** codé en dur (`ScoringRules()` par défaut) en attendant le back-office.
3. **Couverture football-data.org** limitée aux compétitions européennes : CAN, CAF et championnats locaux demandent API-Football.
4. Avertissement de dépréciation `httpx` / `starlette.testclient` (sans effet aujourd'hui).

Réglé à l'étape 1 de la PARTIE 2 : `.venv` recréé en Python 3.12, couplage à API-Football, compétition démo identifiée par un faux `api_id`, README limité à API-Football. Étape 3 : planification (SPEC §10) via `/internal/sync` + GitHub Action, CLAUDE.md sans APScheduler.
