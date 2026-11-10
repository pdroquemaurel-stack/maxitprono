# MaxitProno — État des lieux

Mis à jour le 10 novembre 2026, après la nouvelle barre de navigation, les deux accueils (visiteur, joueur) et la stabilisation du Profil. **Toutes les étapes du découpage (SPEC §12) sont faites**.

## 1. Avancement des étapes (SPEC §12)

| # | Étape | État | Fichiers concernés |
|---|-------|------|--------------------|
| 1 | Squelette, config, base, accueil, déploiement Render | **Fait** | `app/main.py`, `app/config.py`, `app/db.py`, `render.yaml`, `alembic.ini`, `migrations/` |
| 2 | Clients fournisseurs (football-data.org, API-Football), import compétitions/matchs, script de couverture | **Fait** | `app/providers/` (`base.py`, `football_data.py`, `api_football.py`), `app/jobs/import_competitions.py`, `app/jobs/import_matches.py`, `scripts/check_coverage.py`, `scripts/run_import.py`, `scripts/activate_competition.py`, `scripts/reset_football_data.py` |
| 3 | Comptes joueurs (pseudo + PIN, profil, règlement) | **Fait** | `app/auth/` (`pin_auth.py`, `session.py`), `app/services/accounts.py`, `app/services/avatars.py`, `app/routes/accounts.py`, templates `register/login/profile/rules` |
| 4 | Pronostics + clôture 10 min | **Fait** | `app/models/prediction.py`, `app/services/deadlines.py`, `app/services/predictions.py`, `app/routes/matches.py`, `matches.html`, `_match_card.html` |
| 5 | Points + classements + départage | **Fait** | `app/services/scoring.py`, `app/services/ranking.py`, `app/services/leaderboards.py`, `app/jobs/score_predictions.py`, `app/routes/leaderboard.py`, `app/routes/results.py` |
| 6 | Ligues privées + lien de partage | **Fait**, écrans refaits le 9 novembre | Tables `leagues` (+ `color`), `league_members`, `league_competitions`, `app/services/leagues.py` (règles pures), `app/services/league_store.py`, `app/routes/leagues.py`, templates `leagues`, `league`, `league_new`, `league_ready`, `league_settings`, `_league_bits`, `_league_form`, `join`, `_invite`, `static/js/league.js`. `app/services/activity.py`, `leaderboard(league_id=…)`, accueil et onglet « Ligue ». carte « Les pronos de la ligue » sur « Match clôturé » (`app/routes/results.py`) |
| 7 | Pourcentages 1/N/2 | **Fait** | `app/services/probabilities.py`, `app/jobs/import_probabilities.py`, `Match.prob_home/draw/away`, `get_probabilities` des fournisseurs, `_match_card.html` |
| 8 | Back-office admin + KPIs | **Fait** | Accès admin (`users.is_admin`, `scripts/make_admin.py`, `require_admin`), réglages du jeu (`game_settings`, `app/services/game_settings.py`, `settings_store.py`, `/admin/settings`). compétitions et matchs (`/admin/competitions`, `/admin/matches`, `app/services/admin_matches.py`, `Match.score_locked`). KPIs sur `/admin` (`app/services/kpis.py`, `kpi_store.py`) |
| 9 | Traductions FR/EN, page d'erreur, finitions mobile | **Fait** | Langue au choix du joueur : `pick_language` / `set_language` (`app/i18n/__init__.py`), middleware dans `app/main.py`, route `/language/{fr,en}`, `_language.html` (276 clés FR/EN). pages d'erreur 404/500 (`error.html`, gestionnaires dans `app/main.py`), page hors connexion (`offline.html`, `static/js/sw.js` servi en `/sw.js`). finitions mobile (compression, cache, icônes, saisies 16 px, écussons des résultats) |

Hors découpage : `scripts/seed_demo.py` (données de démo sans API ; les joueurs fictifs pronostiquent aussi les matchs ouverts des compétitions actives, réels compris, pour afficher la tendance 1/N/2 ; `--reset` supprime ces pronostics) ; gestion du fuseau horaire du joueur (`app/services/timezones.py`, `static/js/timezone.js`, cookie `tz`).

## 2. Fournisseurs de données

- **Choix par `DATA_PROVIDER`** (`app/providers/__init__.py`, `make_provider`) : `football_data` (défaut, POC) ou `api_football`.
- **Interface** `FootballProvider` (`app/providers/base.py`) : `list_competitions()` et `get_matches(...)`, qui renvoient des dictionnaires déjà à notre format. La conversion des réponses (statuts, scores, logos) est propre à chaque client ; le reste de l'app ne voit jamais le format brut.
- **football-data.org** (`FootballDataClient`) : API v4, en-tête `X-Auth-Token`, 1 appel pour la liste des compétitions, 1 par compétition et par période pour les matchs. Compétitions du POC : `CL`, `PL`, `PD`, `FL1`, `SA`, `BL1` (pas de CAN, CAF, Elite One ni Burkina sur l'offre gratuite). Tirs au but retirés du score final. Vérifié sur l'API réelle le 4 novembre 2026.
- **API-Football** (`ApiFootballClient`) : inchangé côté appels, conversion déplacée dans le module du client.
- **Journal** `api_call_logs` : une ligne par appel avec le fournisseur, l'endpoint, les paramètres, le code HTTP, le quota restant (par jour chez API-Football, par minute chez football-data) et l'erreur.
- **Journée** : `matches.matchday`, `matchday` chez football-data.org, tiré de `league.round` chez API-Football (« Regular Season - 12 » -> 12) ; vide en phase à élimination directe. Les matchs déjà importés la reçoivent à la prochaine synchro.
- **Identifiants** : `provider` + `external_id` (texte) sur `competitions` et `matches`, uniques ensemble. Les imports ne touchent que les données du fournisseur actif. Compétition démo : `provider = "demo"`.
- **Pas de table « équipes »** (choix assumé pour le POC) : noms et logos stockés à plat dans `matches`.
- **Changement de fournisseur** : `scripts/reset_football_data.py`. Simulation par défaut ; avec `--yes`, supprime les compétitions des autres fournisseurs, leurs matchs (y compris ceux ajoutés à la main) et les pronostics sur ces matchs, puis enregistre les compétitions du fournisseur actif (inactives). Joueurs, journal des appels et démo conservés (démo supprimée avec `--include-demo`). La base locale contient encore 12 compétitions API-Football (22 matchs, 0 prono) : le script n'a été lancé qu'en simulation.
- **Synchronisation automatique** : `POST /internal/sync?task=fixtures|scores` (`app/routes/internal.py`), protégée par `Authorization: Bearer <SYNC_TOKEN>` (401 si jeton faux, 503 si `SYNC_TOKEN` vide, 502 avec le message si le fournisseur échoue). Points calculés après chaque passage. Appelée par `.github/workflows/sync.yml` : `fixtures` à 04:00 UTC, `scores` toutes les 10 min (aucun appel API sans match en cours), plus un lancement manuel. Testée en local de bout en bout le 4 novembre 2026 (14 matchs de Ligue 1 importés).
- **Pourcentages 1/N/2** : prédictions du fournisseur (API-Football `/predictions`, 1 appel par match, au plus 20 par import quotidien, matchs des 3 prochains jours) stockées dans `matches.prob_*` ; football-data.org n'en a pas (aucun appel). **Les cartes de match n'affichent plus que la tendance des joueurs** (barre 1/N/2 depuis le 10 novembre, `trends_by_match` dans `app/routes/matches.py`) : calculée à l'affichage à partir de 5 pronostics, visible avant la clôture. Les pourcentages du fournisseur restent importés mais ne sont plus montrés. Arrondi à 100 % par la méthode du plus fort reste.
- **Page Pronos** : filtres et compteurs dans `app/services/match_filters.py` (fonctions pures, même tri en JS dans `static/js/matches.js`) ; clé de compétition = code court sans accent (« l1 », « pl », « cl », id ajouté en cas de doublon). Tous les matchs restent dans la page, un filtre les masque : les scores saisis sont gardés et « Valider » envoie aussi les matchs masqués (`static/js/predictions.js`, un `POST /matches/{id}/prediction` par match modifié). Minute de jeu : `matches.minute`, remplie par la synchro des scores seulement ballon en jeu (API-Football `fixture.status.elapsed` pour 1H, 2H, ET, LIVE ; football-data.org `minute` pour IN_PLAY, **absente de l'offre gratuite**, vérifié le 10 novembre 2026), vide à la mi-temps, après le match et après une correction admin ; pastille « En direct · 54' », sinon « En direct ». Jusqu'à 10 min de retard (fréquence de la synchro), affichée telle quelle.
- **En local** : scripts manuels (`check_coverage`, `run_import`, `run_import --scores`).

## 2 bis. Ligues privées

Écrans refaits le 9 novembre 2026 (« lot 1 »), même charte que la page Profil. Le fil de discussion, le duel de la semaine, la ligue événement « Défi des pays » et le barème « Expert » ont été proposés puis **écartés** : ils ne sont pas prévus (SPEC §7 : pas de chat ni de commentaires).

- **Création** (`/leagues/new`) par un joueur, qui en devient admin et membre : nom de **3 à 30 caractères** (une ligue créée avant le 9 novembre peut garder son nom de 31 à 40 caractères tant qu'il n'est pas modifié), **couleur** de l'icône (orange, noir, vert, pêche ; `leagues.color`), **compétitions** comptées (table `league_competitions` ; aucune ligne = toutes), aperçu en direct. Le barème affiché est celui du jeu (réglé dans le back-office), il n'y a pas de barème par ligue. Puis écran de succès `/leagues/{id}/ready` : code, lien, WhatsApp, « Copier le lien ».
- **Code d'invitation** de 6 caractères sans 0/O/1/I/L, affiché en deux groupes (`K7P-M4X`, `format_code`) et tapé librement (minuscules, espaces, tirets acceptés).
- **Limites** : taille maximale réglée dans le back-office (100 par défaut), 10 ligues par joueur.
- **Rejoindre** : par code sur `/leagues`, avec un message clair pour un code inconnu, une ligue pleine ou si l'on est déjà membre. Ou par lien court **`/j/{code}`**, qui redirige vers `/join/{code}` (toujours valable) : la page affiche la ligue et un bouton, l'adhésion se fait toujours par **POST** (les aperçus de lien de WhatsApp ne font jamais adhérer). Sans compte : l'**inscription ou la connexion** depuis le lien (paramètre `next`) **fait rejoindre la ligue directement** (`join_from_invite`), puis ouvre la ligue.
- **Lien personnel** : chaque membre partage `/j/CODE?ref=<son id>` ; le parrain est gardé à travers l'inscription ou la connexion et enregistré dans `league_members.invited_by_id` s'il est membre de la ligue (ignoré sinon). Code tapé à la main : pas de parrain.
- **Partage** : bouton « Inviter par WhatsApp » (`wa.me` + message) ; si la web-view refuse d'ouvrir le lien, partage natif du téléphone. « Copier » utilise le presse-papiers, sinon le partage natif. `render.yaml` démarre uvicorn avec `--forwarded-allow-ips='*'` pour que les liens partagés soient en https.
- **Mes ligues** (`/leagues`) : créer / rejoindre côte à côte, carte noire « N pronos à faire » (masquée s'il n'y en a pas), puis une carte par ligue : icône colorée, membres et compétitions, ma place (« 3e ») et son évolution (▲ / ▼ / =), 3 avatars + « +N », dernière activité. État vide illustré sans ligue.
- **Détail** (`/leagues/{id}`) :
  - en-tête noir avec menu « … » (réglages ou membres, quitter, retirer un membre, supprimer) et les cartes ma place / mes points / écart avec le 1er ;
  - carte d'invitation ;
  - **prochain match** des compétitions de la ligue, avec compte à rebours, tendance V/N/D de la ligue et qui a déjà joué. **Les scores des autres ne quittent jamais le serveur avant le coup d'envoi** ;
  - onglet **Classement** : podium 2 – 1 – 3, liste à partir du 4e (7 lignes plus la mienne, puis « Voir les N membres » avec `?all=1`), membres pas encore classés en fin de liste, Joueur de la semaine et Lanterne rouge ;
  - onglet **Matchs** : un match terminé au choix (10 derniers), score final et pronos de chaque membre avec ses points. Seuls les matchs terminés sont proposés.
- **Évolution des places** : classement actuel comparé à celui de la veille du dernier jour de matchs comptés (comme sur le Profil). **Joueur de la semaine / Lanterne rouge** : semaine (lundi-dimanche) de ce dernier jour ; pas de lanterne rouge s'il n'y a qu'un joueur.
- **Réglages** (`/leagues/{id}/settings`) : l'admin modifie nom, couleur et compétitions, retire un membre, supprime la ligue (confirmation) ; il ne peut pas la quitter. Un membre y voit la liste et peut quitter. Un non-membre reçoit une 404.
- **Classement de la ligue** : membres seulement, et pour chacun les matchs commencés **après son arrivée** (`league_members.joined_at`), dans les **compétitions de la ligue** (`league_competition_filter`, appliqué partout : accueil, onglet « Ligue » des classements, Profil, fil d'activité). Onglet « Ligue » en tête des classements, ouvert par défaut pour un membre.
- **Ligue principale** (cookie `league`) : la dernière ligue ouverte (`/leagues/{id}`), sinon la plus récemment rejointe ; `/?league=<id>` marche encore. Elle sert à l'accueil (mini-carte), au Profil, aux Résultats et à l'onglet « Ligue » des classements. L'onglet « Ligues » de la barre du bas est actif sur `/leagues`, `/join` et `/j/`.
- **Match clôturé** : carte « Les pronos de la ligue » (ligue choisie sur l'accueil), seulement après la clôture.
- **Migration** `a7b8c9d0e1f2` : `leagues.color` (orange par défaut) et `league_competitions`. Les ligues existantes deviennent orange et comptent toutes les compétitions.

## 2 ter. Back-office

- **Accès** : drapeau `users.is_admin`, donné par `python -m scripts.make_admin <pseudo>` ; les pages `/admin/…` utilisent la connexion normale et répondent **403** aux autres joueurs (404 avant le 10 novembre 2026). Lien « Administration » dans « Modifier mon profil » (`/profile/edit`) pour les admins seulement.
- **Personnalisation** (`/admin/branding`, tables `branding` à une ligne et `branding_changes` pour l'historique) : nom de l'application, logo en deux parties, nom de l'éditeur, slogan FR/EN (2-30 caractères, slogan 2-60, `< > { }` refusés), couleur principale et couleur sombre (#RRGGBB). Teintes dérivées et texte noir/blanc sur la couleur principale calculés (`app/services/branding.py`, contraste WCAG ≥ 4.5:1, même calcul en JS pour l'aperçu dans `static/js/branding.js`). Réglages gardés en mémoire (`branding_store.py`, relus au plus une fois par minute, mis à jour aussitôt à l'enregistrement), injectés en variables CSS `--color-…` (`_brand_style.html`) et en variables de template (`app_name`, `logo_part1`, `logo_part2`, `publisher_name`, `tagline`) ; `t()` remplace `{app_name}` et `{publisher_name}` dans les traductions. Icône d'onglet dynamique `/icon.svg`.
- **Réglages du jeu** (`/admin/settings`, table `game_settings` à une ligne, valeurs par défaut tant que rien n'est enregistré) : points du bon vainqueur (0-20), bonus du score exact (0-20), taille maximale des ligues (2-1000).
- **Changement de barème** : **recalcul complet** de tous les pronostics déjà notés (`rescore_all`), tous les classements suivent. La page des règles et le compteur « N / max membres » affichent les valeurs réglées. Une ligue déjà plus grande qu'une nouvelle limite garde ses membres mais n'en accepte plus.
- **Compétitions** (`/admin/competitions`) : interrupteur actif / inactif par compétition ; bouton « Actualiser la liste du fournisseur » (1 appel, nouvelles compétitions inactives). `scripts/activate_competition.py` reste pour le local.
- **Correction d'un match** (`/admin/matches/{id}`, matchs des 7 derniers et 7 prochains jours) : statut et score final ; points recalculés aussitôt (remis à vide si le match repasse « à venir » ou « en cours »). Le match passe en **`score_locked`** : la synchro met encore à jour noms, logos et horaire, mais plus le statut ni le score. Bouton « Rendre la main à la synchronisation ».
- **Match ajouté à la main** (`/admin/matches/new`) : compétition active, équipes, date et heure saisies dans le fuseau de l'admin (stockées en UTC) ; sans fournisseur, jamais touché par la synchro, initiales à la place des écussons.
- **KPIs** (`/admin`) : joueurs inscrits (démo à part), ligues, pronostics, appels API des 7 derniers jours avec le nombre d'erreurs et la dernière erreur ; tableau des 8 dernières semaines (lundi-dimanche, UTC, démo exclue) : nouveaux inscrits, **joueurs actifs** (ont fait ou modifié au moins un prono dans la semaine), pronos faits par joueur actif, ligues créées. Seules les 8 semaines sont lues en base.

## 2 quater. Langue (étape 9a)

- **Ordre** : choix du joueur (cookie `lang`, un an), sinon langue du téléphone (`Accept-Language`, la première langue connue l'emporte), sinon français. Cookie seul : rien n'est enregistré sur le compte (Max it passera sa langue plus tard par le même mécanisme).
- **Mise en œuvre** : un middleware pose la langue de la requête ; `t()`, les dates, les temps relatifs, les noms de pays, `<html lang>` et les messages construits côté serveur (texte WhatsApp) la suivent sans paramètre.
- **Choix** : liens « Français · English » (`/language/{fr,en}?next=…`) sur « Modifier mon profil », l'accueil sans compte, la connexion et l'inscription.

## 2 quinquies. Erreurs et hors connexion (étape 9b)

- **404 / 500** : pages aux couleurs du jeu avec « Réessayer » (recharge la même adresse) et « Retour à l'accueil », dans la langue du joueur ; une 500 est journalisée (logs Render). La route `/internal/sync` garde des erreurs en JSON (appelée par un robot).
- **Pas de connexion** (SPEC §8) : service worker minimal (`/sw.js`) qui garde seulement `/offline`, la feuille de style et les polices. Si une page ne répond pas, il affiche « Pas de connexion » + « Réessayer », et la page se recharge seule au retour du réseau. Rien d'autre n'est gardé : les données restent toujours fraîches. Sans prise en charge des service workers (peut-être la web-view Max it), rien ne change.
- **Vérifié dans un vrai Chrome** (piloté par le protocole de débogage) : installation en ligne, serveur coupé, navigation → page hors connexion affichée avec ses polices.

## 2 sexies. Finitions mobile (étape 9c)

- **Compression GZip** (`GZipMiddleware` de Starlette, aucune dépendance) : la liste des matchs passe de 39,6 Ko à 3,5 Ko, les autres pages autour de 1,3 Ko, la feuille de style de 24,5 Ko à 5,6 Ko.
- **Cache** : CSS et JS appelés par `static_url()` (`?v=` + empreinte du fichier, recalculée quand il change), gardés un an par le navigateur ; polices gardées un an sans version (même adresse que dans le CSS, préchargées).
- **Icônes** : `static/icons/icon.svg` (onglet) et `apple-touch-icon.png` 180 px (écran d'accueil), `/favicon.ico` ; barre du navigateur en `#F6F7FB`.
- **Saisie** : champs à 16 px (pas de zoom automatique sur iPhone) ; `scroll-padding-bottom` pour que le champ en cours de saisie reste au-dessus du bouton collé et de la barre d'onglets.
- **Écussons** aussi dans la liste des résultats ; noms d'équipe longs coupés en fin de mot ou par trait d'union (plus « Strasbour/g »).
- Onglet « Compét. » (« Comp. » en anglais) : les 5 onglets tiennent à 360 px.
- **Passe à 360 px** en émulation mobile (accueil, pronos, classements, résultats, profil) : aucun débordement horizontal.

## 2 septies. Page Profil (statistiques)

- **`/profile`** : en-tête (logo, engrenage), identité (avatar ou initiales, pays, membre depuis, ligue), sélecteur **Saison / Semaine / Compét.** (`?period=season|week|competition&competition=<id>`) qui filtre toute la page, carte héro (anneau de réussite, points), 3 tuiles, répartition, mes classements (ligue, pays, général), forme sur 10 pronos et séries, par compétition, badges, partage.
- **Calculs** : `app/services/profile_stats.py` (fonctions pures), lectures dans `app/services/profile_store.py`, route `app/routes/profile.py`. Prono joué = match terminé avec un score final ; réussite = (exacts + bons résultats) / joués, arrondie à l'entier (0,5 vers le haut).
- **Saison** = tous les matchs joués (pas de notion de saison commune aux compétitions). **Semaine** = lundi-dimanche UTC, comme les classements ; la carte affiche « Journée N » si tous mes pronos de la semaine sont sur la même journée (`matches.matchday`), sinon « Semaine du … ». **Compét.** = compétition choisie, sinon la Ligue des champions si elle est active, sinon la première active.
- **Évolution dans ma ligue** : rang actuel comparé au rang avant ma dernière journée jouée (2 requêtes de classement).
- **Badges** calculés à la volée sur toute la carrière (pas filtrés par la période) : Prophète (3 exacts), Remontada (+5 places au général en une journée, d'après l'historique des rangs), Rassembleur (au moins un ami entré dans une ligue par mon lien d'invitation), Sans faute (5 pronos réussis d'affilée).
- **Historique des rangs** (`rank_snapshots`, `app/services/rank_history.py`) : rang et points au classement général à la fin de chaque journée de matchs (jour UTC). Refait par les fonctions de calcul des points elles-mêmes (`app/jobs/score_predictions.py`) : après une synchro, à partir de la plus ancienne journée touchée ; après une correction admin, à partir du jour du match ; après un changement de barème, en entier. Table vide (premier passage après déploiement) : tout est reconstruit.
- **`/profile/edit`** (seul accès : l'engrenage, `aria-label` « Paramètres et profil ») : photo avec aperçu, pseudo (aussi identifiant de connexion, unicité vérifiée), pays, langue, mes pronostics, mes ligues, règlement, Administration (admins), déconnexion. Le formulaire poste toujours sur `POST /profile`.
- **`/players/{id}`** (page publique, sans compte) : identité, saison (anneau, points, tuiles, répartition), forme, badges ; aperçu WhatsApp (`og:title`, `og:description`). « Partager mes stats » envoie ce lien, avec `?league=CODE` si le joueur a une ligue : la page propose alors « Rejoindre la ligue » (lien avec `?ref=` du joueur). Cartes communes au profil : `_stats_identity`, `_stats_hero`, `_stats_tiles`, `_stats_form`, `_stats_badges`.
- **`/profile/history`** : l'historique des pronostics, auparavant en bas du profil.
- **Mise en page immobile d'un filtre à l'autre** : chiffres tabulaires, grilles `repeat(N, minmax(0, 1fr))`, hauteurs réservées, textes variables sur une ligne (`.p-one-line`), ligne de hauteur fixe sous le sélecteur (choix de la compétition ou rappel de la période). États vides de même hauteur : « Pas encore de prono sur cette période », Forme toujours en 10 cases, « Par compétition » garde les lignes de toute la carrière (`stable_competition_rows`). Le changement de filtre recharge la page : la transition de 200 ms de l'anneau ne se voit donc pas. Vérifié dans Chromium à 390 et 360 px (67 éléments : mêmes positions et tailles sur les 3 filtres, deux allers-retours).
- Polices de l'app (Outfit pour les titres et chiffres, DM Sans pour le texte) : pas d'Inter ni de Google Fonts, pour garder une seule charte, une page légère en 3G et des polices disponibles hors connexion.

## 3. Déploiement

- `render.yaml` : base Postgres `maxitprono-db` (free, Francfort) + web service Python ; démarrage = `alembic upgrade head && uvicorn …` ; `healthCheckPath: /health`.
- Variables déclarées : `PYTHON_VERSION`, `DATABASE_URL` (depuis la base), `SECRET_KEY` (générée), `DEFAULT_LANGUAGE`, `SECURE_COOKIES`, `API_FOOTBALL_KEY` (sync: false).
- `render.yaml` déclare aussi `DATA_PROVIDER` (football_data), `FOOTBALL_DATA_API_KEY` et `SYNC_TOKEN` (sync: false, à saisir dans Render).
- GitHub Actions : secret `SYNC_TOKEN` et variable `APP_URL` à configurer (voir README).
- `.env.example` : `DATA_PROVIDER`, `FOOTBALL_DATA_API_KEY`, `API_FOOTBALL_KEY`, `DATABASE_URL`, `SECRET_KEY`, `DEFAULT_LANGUAGE`, `SECURE_COOKIES`, `SYNC_TOKEN`.
- `.env` local (noms seulement) : `DATA_PROVIDER`, `FOOTBALL_DATA_API_KEY`, `API_FOOTBALL_KEY`.
- **Tâches planifiées** : GitHub Action `.github/workflows/sync.yml` (pas de planificateur dans l'app). GitHub peut retarder les tâches de quelques minutes et les suspend après 60 jours sans commit.

## 2 octies. Accueil (10 novembre)

- **Barre du bas** : Accueil · Ligues · Pronos · Classements · Profil. `/results` reste accessible (lien depuis l'accueil).
- **Visiteur** (`home_guest.html`, sans barre du bas) : 3 prochains matchs ouverts (lien vers `/register`, compte à rebours sur le plus proche), **compétition du moment** = la plus chargée des 7 prochains jours parmi les compétitions actives (`app/services/home.py`), barème réel du jeu. Pied de page : Règles, puis `/help`, `/privacy`, `/legal`, qui affichent « Contenu à venir » (`coming_soon.html`).
- **Joueur** (`home_player.html`) : la veille = jour du fuseau du joueur (`local_day_bounds`) ; places gagnées d'après `rank_snapshots` (classement général, `places_gained`) ; pronos à faire = 3 premiers matchs ouverts sans prono, enregistrés par « Valider mes pronos » (`predictions.js`, `data-mode="button"`, même `POST /matches/{id}/prediction`) ; « Chez les copains » = 3 derniers événements de toutes mes ligues, sans les miens ni les doublons (`friends_feed`) ; prochain badge avec « N sur M » (`badge_progress`).
- **Compte à rebours** jusqu'à la clôture : `countdown_to_closing` / `format_countdown`, mis à jour chaque minute par `static/js/countdown.js`.
- **Non fait faute de données** : cloche de notifications (aucun système de notifications ; à prévoir avec une date de « dernière visite »). Abréviations calculées par `team_initials` (« MU » et non « MUN ») : le `tla` de football-data.org n'est pas stocké.

## 4. Charte DESIGN.md

Socle en place (`app/static/css/style.css`) : variables de couleur, polices Outfit et DM Sans (hébergées localement, pas via Google Fonts — plus léger), cartes sans ombre, badges, code couleur des scores (`score_colors.py` + `score-colors.js`), barre de navigation à 5 onglets.

| Écran | État |
|-------|------|
| Accueil (visiteur, joueur) | **Refait** le 10 novembre (charte Profil / Ligues) ; vérifié à 390 et 360 px |
| Pronos (`/matches`) | **Refait** le 10 novembre : filtres compétition × statut (`?comp=l1&status=todo|mine|all`, repli localStorage), matchs par jour, ligne de match commune avec l'accueil (pastille d'état, score réel + « Ton prono », barre de tendance des joueurs), bouton « Valider » unique (plus d'enregistrement automatique), confirmation avant de quitter avec des pronos non enregistrés ; vérifié à 390 px |
| Match clôturé | **Conforme** : carte score final (écussons 44 px), bandeau du prono, pronos des membres de la ligue avec leurs points |
| Classements | **Conforme** (liste, onglets) avec l'onglet « Ligue » ; les 5 onglets tiennent à 360 px |
| Résultats | Conforme au style général (pas de maquette dédiée), avec écussons |
| Ligues (mes ligues, détail, création, réglages) | **Refait** le 9 novembre avec la charte de la page Profil ; vérifié à 390 px |
| Profil | Charte Profil ; mise en page immobile entre filtres |
| Connexion, inscription, règles | Composants de base (cartes, formulaires, boutons) ; pas de maquette dédiée |

Écussons d'équipes (`_crest.html`) : logo du fournisseur chargé en différé (`loading="lazy"`), directement depuis le site du fournisseur (pas de copie locale) ; initiales en dessous (`app/services/teams.py`), visibles s'il n'y a pas de logo ou s'il ne charge pas. Affichés sur les cartes de pronos, la liste des résultats et l'écran « Match clôturé ».

## 5. Tests

`pytest` (via `.venv`, **Python 3.12.3**) : **604 tests passent, 0 échec**, 1 avertissement (dépréciation `httpx` dans le TestClient de Starlette).

## 6. Incohérences et dettes

1. **Couverture football-data.org** limitée aux compétitions européennes : CAN, CAF et championnats locaux demandent API-Football.
2. Avertissement de dépréciation `httpx` / `starlette.testclient` (sans effet aujourd'hui).
3. **Mes ligues** fait environ 5 requêtes par ligue (50 au plus avec 10 ligues) : suffisant pour le POC.

Réglé à l'étape 1 de la PARTIE 2 : `.venv` recréé en Python 3.12, couplage à API-Football, compétition démo identifiée par un faux `api_id`, README limité à API-Football. Étape 3 : planification (SPEC §10) via `/internal/sync` + GitHub Action, CLAUDE.md sans APScheduler.
