# MaxitProno — Charte visuelle « Design 2.0 » (thème sombre)

Toute nouvelle page ou tout nouveau composant suit ce document. Les captures de la maquette déposées
dans `docs/design/v2/` font foi. L'ancienne charte (thème clair) est archivée dans `docs/DESIGN-v1.md`.

## 1. Principes
- Une appli professionnelle et aboutie, qui garde un côté social et ludique.
- **Thème sombre unique.** Le fond de l'application est la couleur `color_dark` réglée dans l'admin.
- La couleur principale (orange par défaut) sert à **mettre en avant** : action principale, case à remplir,
  1er du classement, ma ligne, éléments « à faire ». Ce n'est jamais un fond de page.
- Mobile d'abord : largeur de référence 390 px, vérifiée aussi à 360 px. Cibles tactiles de 44 px minimum.
  Pas de défilement horizontal, sauf pour les rangées de pastilles prévues pour défiler.
- Page légère (3G) : pas de dépendance JS ni CSS externe, polices hébergées dans `app/static/fonts`.
- Pas d'ombre portée, pas de dégradé. Les cartes se distinguent par leur fond et une bordure de 1 px.
- Le navigateur ne doit pas retoucher les couleurs : `<meta name="color-scheme" content="dark">`,
  `:root { color-scheme: dark; }`, et `theme-color` = `color_dark` (voir `_brand_style.html`).

## 2. Couleurs

### Couleurs de la marque : réglées dans l'admin, jamais en dur
Admin → Personnalisation enregistre deux couleurs. `palette()` (`app/services/branding.py`, testée dans
`tests/test_branding.py`) en calcule toutes les teintes, injectées dans `<head>` par `_brand_style.html`.
Le même calcul existe en JS (`app/static/js/branding.js`) pour l'aperçu en direct : les deux doivent rester identiques.

| Variable | Défaut | Calcul | Rôle |
|---|---|---|---|
| `--color-primary` | `#FF7900` | choisie | boutons principaux, onglet actif, bordure des cases à remplir, barres de progression |
| `--color-on-primary` | `#000000` | noir ou blanc, le plus contrasté | texte posé sur `--color-primary` |
| `--color-primary-on-dark` | `#FF9A40` | principale + 25 % de blanc, puis plus si contraste < 4.5:1 sur `--color-raised` | liens, textes et chiffres de la couleur principale sur fond sombre |
| `--color-primary-tint` | `rgba(255,121,0,0.14)` | principale à 14 % | pastilles « à faire », fond de ma ligne |
| `--color-primary-deep` | `#301E10` | `mix(primary, dark, 0.85)` | fond d'une case de score vide à remplir |
| `--color-dark` | `#0B0E13` | choisie (texte blanc lisible dessus, contrôlé) | **fond de l'application**, barre de navigation, champs |
| `--color-surface` | `#1A1C21` | `mix(dark, blanc, 0.06)` | cartes |
| `--color-raised` | `#23262B` | `mix(dark, blanc, 0.10)` | carte mise en avant, case remplie, avatars aux initiales |
| `--color-line` | `#2D3034` | `mix(dark, blanc, 0.14)` | bordures de cartes, séparateurs, pistes de barres |
| `--color-line-strong` | `#414347` | `mix(dark, blanc, 0.22)` | bordures de champs et de boutons secondaires, pointillés |

### Couleurs fixes (`:root` de `app/static/css/style.css`)
```css
--text: #F2F4F7;     /* texte principal */
--text-2: #C9D1DB;   /* texte secondaire appuyé */
--muted: #9AA4B2;    /* texte secondaire, libellés */
--faint: #5B6573;    /* uniquement décoratif ou grand (en-têtes de tableau 11 px en majuscules, tirets) */
--good: #3DD68C;  --good-tint: rgba(61,214,140,0.14);  --good-45: rgba(61,214,140,0.45);
--bad: #FF6B6B;   --bad-tint: rgba(255,107,107,0.14);
--draw: #6CB6FF;
--bronze: #C9875A;   /* 3e du classement */
```
Un seul jeu de variables : n'en recréez pas de locales à une page.

### Contrastes (défauts)
| Texte | sur `--color-dark` | sur `--color-surface` | sur `--color-raised` |
|---|---|---|---|
| `--text` | 17.5:1 | 15.5:1 | 13.8:1 |
| `--text-2` | 12.5:1 | 11.1:1 | 9.9:1 |
| `--muted` | 7.7:1 | 6.8:1 | 6.0:1 |
| `--color-primary-on-dark` | 9.2:1 | 8.1:1 | ≥ 4.5:1 (garanti par le calcul) |
| `--faint` | 3.3:1 | 2.9:1 | — réservé au décoratif |

### Règles
- Texte sur `--color-primary` : toujours `--color-on-primary`.
- Texte de la couleur principale sur fond sombre : `--color-primary-on-dark`, jamais `--color-primary`.
- Sur un fond plein `--good` ou `--text` (bouton clair, onglet actif) : texte `--color-dark`.
- Scores affichés (résultats, historique, pronos de la ligue) : chiffre gagnant `--good`, perdant `--bad`, nul `--draw`.
  Les noms d'équipes restent en `--text`.

## 3. Typographie
- Texte et titres : **DM Sans** (`--font-text`, police variable, `dm-sans.woff2`).
- Gros chiffres (scores, cases, points, rangs, pourcentages des tuiles, code d'invitation) :
  **Barlow Condensed 700** (`--font-num`, `barlow-condensed-700.woff2`, licence `OFL-barlow-condensed.txt`).
- Partout : `font-variant-numeric: tabular-nums` (posé sur `body`).
- Tailles : titre de page 24 px / 800 (accueil « Salut … » 26 px) ; titre de section 17 px / 800 ;
  texte 14 px ; secondaire 12–13 px en `--muted` ; petites étiquettes 11 px.
- Chiffres : cases de score 30 px, score réel d'une carte 32 px, tuiles 28–30 px, « Ta position » 36 px,
  points du profil 48 px, score final d'un match clôturé 40 px.
- **Aucun texte tronqué** sur les noms d'équipes, de ligues, de joueurs ni sur les libellés de KPI :
  retour à la ligne (`overflow-wrap`, `hyphens: auto`). Les tuiles réservent 2 lignes de libellé pour garder
  leur hauteur.

## 4. Formes et espacements
- Rayons : cartes 16 px, boutons et cases 12 px, pastilles 999 px, badges 16 px.
- Marges latérales 16–20 px, écart entre cartes 10–12 px, padding des cartes 12–16 px.

## 5. Composants
- **Carte** (`.card`, `.lg-card`, `.p-card`, `.h-card`) : fond `--color-surface`, bordure 1 px `--color-line`, rayon 16 px.
  **Carte mise en avant** (`.card-raised`, « Ta position ») : fond `--color-raised`, bordure 2 px `--color-primary`.
- **Bouton principal** (`button`, `.button`, `.lg-btn-orange`) : fond `--color-primary`, texte `--color-on-primary`,
  44–48 px de haut, rayon 12 px, graisse 800.
  **Bouton secondaire** (`.secondary`, `.lg-btn-light`) : transparent, bordure `--color-line-strong`, texte `--text`.
  **Bouton clair** (`.lg-btn-dark`, « Rejoindre », « Faire mon prono ») : fond `--text`, texte `--color-dark`.
- **Sélecteur segmenté** (`.pr-status`, `.lg-segments`, `.p-segments`) : conteneur `--color-surface`, bordure,
  4 px de padding ; onglet actif fond `--text`, texte `--color-dark`, gras ; onglets de largeur fixe
  (le gras ne décale rien).
- **Pastilles de filtre** (`.chip`, `.pr-comp`, `.lg-chip`) : 36 px (zone tactile étendue à 44 px), rayon max.
  Active : fond `--text`, texte `--color-dark`. Inactive : `--color-surface`, bordure `--color-line`.
- **Pastilles d'état** (`.mc-pill`) : « À jouer » / « Ferme dans … » `--color-primary-tint` + `--color-primary-on-dark` ;
  « Prono enregistré » `--good-tint` + `--good` ; « En direct » `--bad-tint` + `--bad` ; les autres en `--color-raised` + `--muted`.
- **Points gagnés** (`points_pill`, `.badge.points`) : score exact fond `--good` texte `--color-dark` ;
  bon résultat `--good-tint` + `--good` ; 0 `--bad-tint` + `--bad`. Valeurs = barème du back-office.
- **Évolution** (`move_badge`) : ▲ N `--good`, ▼ N `--bad`, « = » `--faint`.
- **Avatars** (`avatar()` de `_league_bits.html`) : ronds, photo ou initiales (`--color-raised`, `--text-2`).
  Piles qui se chevauchent de 8 px, anneau de 2 px de la couleur du fond derrière. Le joueur courant a un anneau orange.
- **Écussons** (`_crest.html`) : ronds sur `--color-raised`, logo en retrait de 16 % ; 48 px sur les cartes de match,
  32–40 px dans les listes. Repli : abréviation de l'équipe.
- **Logo de l'appli** (`_logo.html`) : `logo_part1` en `--text` + `logo_part2` dans une pastille `--color-primary`.
- **Barre de navigation** (5 onglets) : fond `--color-dark`, bordure haute `--color-line` ; actif icône `--color-primary`
  et libellé `--text` gras, inactifs `--muted`.
- **Champs** : fond `--color-dark`, bordure `--color-line-strong`, texte `--text`, contour 2 px `--color-primary` au focus.

## 6. Écrans de référence
1. **Pronos** (`/matches`, écran de référence)
   - En-tête : titre, pastille « N à faire » (point orange), avatar.
   - Bande des 5 premiers jours qui ont des matchs (jour abrégé 11 px + numéro 17 px), collée en haut ; jour courant
     souligné de 2 px orange ; point orange = matchs encore à pronostiquer. Un clic fait défiler jusqu'au jour (ancre).
   - Pastilles des compétitions, puis sélecteur À jouer / Mes pronos / Tous.
   - Par jour : carte d'avancement « Mer. 11 nov. · 2 sur 3 joués », « Ferme dans X h Y », barre 4 px.
   - **Carte match** (`_match_card.html`, partagée avec l'accueil) : grille `minmax(0,1fr) 132px minmax(0,1fr)` ;
     en haut emblème + « Compétition · J12 » et pastille d'état ; au centre logo 48 px au-dessus du nom complet,
     deux cases 48×52 séparées par « : », heure dessous ; case à remplir fond `--color-primary-deep` + bordure 2 px
     `--color-primary`, case remplie `--color-raised` + bordure `--color-line-strong`. Match en cours ou terminé :
     score réel, « Ton prono X : Y », pastille de points. Dessous, pour un match ouvert : tendance des joueurs
     (barre de 6 px domicile `--text` / nul `--color-line-strong` / extérieur `--color-primary`,
     puis « FCB 78 % · Nul 12 % · KOE 10 % »), place gardée sous 5 pronos.
   - Barre de validation : carte claire (`--text`, texte `--color-dark`) au-dessus de la navigation,
     « N pronos à faire », « Modifiable jusqu'à 10 min avant », bouton orange « Valider ».
2. **Accueil joueur** : « Salut pseudo » 26 px, la veille (gains en `--good`), 3 tuiles (place, points en orange,
   réussite) ; « À jouer maintenant » (prochain match ouvert, carte à bordure orange, Valider, « Voir tous les matchs ») ;
   résultats d'hier ; carrousel Mes ligues ; Chez les copains ; prochain badge.
3. **Ligues** : Créer (carte orange, + sur carré sombre) et Rejoindre (champ + bouton clair) côte à côte ;
   une carte par ligue (icône 48 px, nom, méta, place 30 px + évolution, séparateur, avatars, dernière activité).
4. **Détail d'une ligue** : retour + menu, icône 60 px, nom 22 px, méta, 3 tuiles, ligne du code (copier + « Inviter »),
   prochain match, onglets Classement / Matchs ; podium 2-1-3 (marche du 1er orange 88 px + couronne, 2e `--color-line`,
   3e `--color-raised`) puis liste à partir du 4e ; onglet Matchs : score final 40 px coloré et pronos des membres.
5. **Classements** : titre + « Règles », pastilles de type, ligne d'explication, carte « Ta position », tableau
   `30px 1fr 44px 52px` (# · Joueur · Exacts · Pts, en-tête 11 px `--faint`), rangs 1-3 orange / blanc / bronze,
   ma ligne teintée avec liseré gauche de 3 px orange ; règle des ex æquo en 12 px.
6. **Profil** : identité, sélecteur de période, anneau 108 px (piste `--color-line`, arc `--color-primary`) + points 48 px,
   3 tuiles 28 px, répartition (barre 10 px exact / bon résultat `--good-45` / raté + 3 colonnes), forme en 10 cases de 30 px,
   séries sur `--color-dark`, badges en carrés de 54 px (pointillés si verrouillés), Partager / Défier.
   **Les blocs ne bougent pas quand on change de période** (hauteurs réservées).
7. **Autres pages** (visiteur, connexion, inscription, règlement, admin, création et réglages de ligue, modification du
   profil, résultats, erreurs, hors connexion) : même thème, sans refonte de leur contenu.

## 7. Pas encore affiché (données absentes)
Joker ×2, points dans l'en-tête de Pronos, évolution au classement général, non-lus des ligues, ligue événement
« OFFICIELLE » et barres des pays, onglet Fil, carte Duel de la semaine. Ne les ajoutez qu'avec leurs données.
