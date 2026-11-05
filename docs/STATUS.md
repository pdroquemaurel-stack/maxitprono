# MaxitProno — État des lieux

Mis à jour le 4 novembre 2026, après l'étape 5 de la PARTIE 2 (ligues privées terminées).

## 1. Avancement des étapes (SPEC §12)

| # | Étape | État | Fichiers concernés |
|---|-------|------|--------------------|
| 1 | Squelette, config, base, accueil, déploiement Render | **Fait** | `app/main.py`, `app/config.py`, `app/db.py`, `render.yaml`, `alembic.ini`, `migrations/` |
| 2 | Clients fournisseurs (football-data.org, API-Football), import compétitions/matchs, script de couverture | **Fait** | `app/providers/` (`base.py`, `football_data.py`, `api_football.py`), `app/jobs/import_competitions.py`, `app/jobs/import_matches.py`, `scripts/check_coverage.py`, `scripts/run_import.py`, `scripts/activate_competition.py`, `scripts/reset_football_data.py` |
| 3 | Comptes joueurs (pseudo + PIN, profil, règlement) | **Fait** | `app/auth/` (`pin_auth.py`, `session.py`), `app/services/accounts.py`, `app/services/avatars.py`, `app/routes/accounts.py`, templates `register/login/profile/rules` |
| 4 | Pronostics + clôture 10 min | **Fait** | `app/models/prediction.py`, `app/services/deadlines.py`, `app/services/predictions.py`, `app/routes/matches.py`, `matches.html`, `_match_card.html` |
| 5 | Points + classements + départage | **Fait** | `app/services/scoring.py`, `app/services/ranking.py`, `app/services/leaderboards.py`, `app/jobs/score_predictions.py`, `app/routes/leaderboard.py`, `app/routes/results.py` |
| 6 | Ligues privées + lien de partage | **Fait** | Tables `leagues` + `league_members`, `app/services/leagues.py` (règles pures), `app/services/league_store.py`, `app/routes/leagues.py`, templates `leagues`, `league`, `join`, `_invite`. `app/services/activity.py`, `leaderboard(league_id=…)`, accueil et onglet « Ligue ». carte « Les pronos de la ligue » sur « Match clôturé » (`app/routes/results.py`) |
| 7 | Pourcentages 1/N/2 | **Fait** | `app/services/probabilities.py`, `app/jobs/import_probabilities.py`, `Match.prob_home/draw/away`, `get_probabilities` des fournisseurs, `_match_card.html` |
| 8 | Back-office admin + KPIs | **À faire** | Remplacé provisoirement par `scripts/activate_competition.py` ; barème figé dans `ScoringRules()` |
| 9 | Traductions FR/EN, page d'erreur, finitions mobile | **Partiel** | `app/i18n/fr.json` et `en.json` complets (200 clés chacun, mêmes clés) ; mais la langue est figée sur `DEFAULT_LANGUAGE` (`app/templating.py`), pas de choix par le joueur ; pas de page « erreur réseau + réessayer » (`_error.html` n'est qu'un message de formulaire) |

Hors découpage : `scripts/seed_demo.py` (données de démo sans API ; les joueurs fictifs pronostiquent aussi les matchs ouverts des compétitions actives, réels compris, pour afficher la tendance 1/N/2 ; `--reset` supprime ces pronostics) ; gestion du fuseau horaire du joueur (`app/services/timezones.py`, `static/js/timezone.js`, cookie `tz`).

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
- **Pourcentages 1/N/2** : prédictions du fournisseur (API-Football `/predictions`, 1 appel par match, au plus 20 par import quotidien, matchs des 3 prochains jours) stockées dans `matches.prob_*` ; football-data.org n'en a pas (aucun appel). À défaut, **tendance des joueurs** calculée à l'affichage à partir de 5 pronostics, visible avant la clôture, avec la mention « Tendance des joueurs ». Arrondi à 100 % par la méthode du plus fort reste.
- **En local** : scripts manuels (`check_coverage`, `run_import`, `run_import --scores`).

## 2 bis. Ligues privées

- **Création** par un joueur, qui en devient admin et membre. Nom de 3 à 40 caractères, **code d'invitation** de 6 caractères sans 0/O/1/I/L (ex. `K7PM4X`), tapé librement (minuscules, espaces, tirets acceptés).
- **Limites** : 100 membres par ligue (constante `MAX_MEMBERS`, en attendant le back-office), 10 ligues par joueur.
- **Rejoindre** : par code (`/leagues`) ou par lien `/join/{code}`. Le lien affiche la ligue et un bouton ; l'adhésion se fait toujours par **POST** (les aperçus de lien de WhatsApp ne font jamais adhérer). Sans compte : inscription ou connexion puis **retour au lien** (paramètre `next`, limité aux chemins du site).
- **Partage** : bouton « Inviter des potes par WhatsApp » (`wa.me` + message), partage natif du téléphone s'il existe (`static/js/share.js`). `render.yaml` démarre uvicorn avec `--forwarded-allow-ips='*'` pour que les liens partagés soient en https.
- **Admin** : retire un membre, supprime la ligue (confirmation) ; ne peut pas la quitter. Un membre peut la quitter. Un non-membre reçoit une 404.
- **Classement de la ligue** : membres seulement, et pour chacun les matchs commencés **après son arrivée** (`league_members.joined_at`). Onglet « Ligue » en tête des classements, ouvert par défaut pour un membre (menu si plusieurs ligues) ; les 5 onglets défilent horizontalement sur petit écran.
- **Accueil « Ma ligue »** : sélecteur de ligue (menu `<details>`, sans JavaScript ; choix mémorisé dans le cookie `league`, par défaut la ligue rejointe en dernier), podium et nombre de joueurs de la ligue, fil « Dans la ligue » (créée / a rejoint / score exact, 5 événements des 7 derniers jours, temps relatif « 2 h », « hier »), bouton d'invitation WhatsApp. Sans ligue : podium général et carte « Joue avec tes potes ». « a pronostiqué les 5 matchs du week-end » (maquette) reporté.
- **Match clôturé** : carte « Les pronos de la ligue » (ligue choisie sur l'accueil) avec le score pronostiqué coloré et le badge de points de chaque membre ; moi d'abord, puis par points, les membres sans prono en dernier. Seulement après la clôture : avant, on ne voit jamais les pronos des autres (seulement la tendance 1/N/2).
- Après connexion demandée par une page, retour à cette page (`/login?next=…`).

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
| Accueil (Ma ligue) | **Conforme** : sélecteur de ligue, podium de la ligue, carte « matchs sans prono », fil « Dans la ligue », bouton d'invitation WhatsApp (bordure orange pointillée) |
| Pronos (saisie directe) | **Conforme** : cases de score colorées, état « Ferme dans… », bouton collé en bas, ligne 1/N/2, écussons 36 px au-dessus des noms |
| Match clôturé | **Conforme** : carte score final (écussons 44 px), bandeau du prono, pronos des membres de la ligue avec leurs points |
| Classements | **Conforme** (liste, onglets) avec l'onglet « Ligue » |
| Résultats | Conforme au style général (pas de maquette dédiée) |
| Profil, connexion, inscription, règles | Composants de base (cartes, formulaires, boutons) ; pas de maquette dédiée |

Écussons d'équipes (`_crest.html`) : logo du fournisseur chargé en différé (`loading="lazy"`), directement depuis le site du fournisseur (pas de copie locale) ; initiales en dessous (`app/services/teams.py`), visibles s'il n'y a pas de logo ou s'il ne charge pas. Affichés sur les cartes de pronos et l'écran « Match clôturé », pas encore dans la liste des résultats.

## 5. Tests

`pytest` (via `.venv`, **Python 3.12.3**) : **396 tests passent, 0 échec**, 1 avertissement (dépréciation `httpx` dans le TestClient de Starlette).

## 6. Incohérences et dettes

1. **Langue non sélectionnable** par le joueur (§1, étape 9).
2. **Barème de points** codé en dur (`ScoringRules()` par défaut) en attendant le back-office.
3. **Couverture football-data.org** limitée aux compétitions européennes : CAN, CAF et championnats locaux demandent API-Football.
4. Avertissement de dépréciation `httpx` / `starlette.testclient` (sans effet aujourd'hui).

Réglé à l'étape 1 de la PARTIE 2 : `.venv` recréé en Python 3.12, couplage à API-Football, compétition démo identifiée par un faux `api_id`, README limité à API-Football. Étape 3 : planification (SPEC §10) via `/internal/sync` + GitHub Action, CLAUDE.md sans APScheduler.
