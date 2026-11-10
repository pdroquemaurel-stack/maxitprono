# MaxitProno — Charte visuelle (piste F · Entre potes, accents Orange)

À placer dans `docs/DESIGN.md`. Les maquettes de référence sont dans `docs/design/` (captures des 3 écrans).
Toute nouvelle page ou composant suit ce document. En cas de doute, la maquette fait foi.

## 1. Principes
- Fond clair et neutre. L'orange **#FF7900** n'est jamais un fond de page : il sert uniquement à mettre en avant
  (action principale, 1er du classement, score exact, éléments « à faire »).
- La ligue d'amis est au centre de l'expérience (accueil = ma ligue).
- Les pronostics de la journée se saisissent directement dans la liste (deux cases de score par match, un seul bouton d'enregistrement).
- Les pronos des autres membres ne s'affichent qu'après la clôture du match.
- Mobile d'abord : largeur de référence 390 px, cibles tactiles de 44 px minimum.

## 2. Couleurs (variables CSS à définir dans `app/static/css/style.css`)
```css
:root {
  /* Fonds et texte */
  --bg: #F6F7FB;           /* fond de page */
  --surface: #FFFFFF;      /* cartes */
  --border: #E6E8F2;       /* bordures de cartes */
  --ink: #161A33;          /* texte principal, cartes sombres (podium, score final) */
  --ink-2: #2B2F4A;        /* éléments secondaires sur carte sombre */
  --muted: #5A5F7A;        /* texte secondaire */
  --placeholder: #A9AFC4;

  /* Orange : mise en avant uniquement */
  --orange: #FF7900;       /* fonds de boutons, badges, 1er, score exact — texte posé dessus en noir #000 */
  --orange-text: #B34F00;  /* orange lisible pour du TEXTE sur fond clair (liens, onglet actif) */
  --orange-soft: #FFF1E6;  /* fond léger (avatars, badge « bon vainqueur ») */

  /* Code couleur des scores (chiffres uniquement, jamais les noms d'équipes) */
  --win: #1E8A55;   --win-bg: #EAF6EF;    /* équipe donnée gagnante */
  --lose: #D12E1B;  --lose-bg: #FCECEA;   /* équipe donnée perdante */
  --draw: #1C7FB5;  --draw-bg: #E8F3FA;   /* les deux chiffres si nul */

  /* Variantes sur carte sombre (--ink) */
  --win-on-dark: #50BE87;
  --lose-on-dark: #F0644E;
}
```
Règles :
- Texte sur fond orange : toujours noir `#000000`.
- Ne jamais écrire du texte en `--orange` sur fond clair (contraste insuffisant) : utiliser `--orange-text`.
- Le code vert/rouge/bleu s'applique aux **chiffres** du score (pronostic du joueur, score final, pronos de la ligue). Les noms d'équipes restent en `--ink`.
- Case de score vide : bordure `#D5D8E5`, fond `--bg`.

## 3. Typographie (Google Fonts)
- Titres et chiffres : **Outfit** 700/800.
- Texte : **DM Sans** 400/500/600/700.
- Tailles : titre de page 26 px, titre de section 17–18 px, texte 15–16 px, libellés 12–13 px, score principal 48 px, cases de score 22 px.

## 4. Formes et espacements
- Rayons : cartes 16–18 px, grandes cartes 22 px, boutons 16 px, cases de score 12 px, badges 10 px.
- Espacements : marges latérales 16–20 px, écart entre cartes 10–16 px, padding des cartes 12–16 px.
- Pas d'ombres portées, pas de dégradés. Bordure 1 px `--border` sur les cartes blanches.

## 5. Composants
- **Bouton principal** : hauteur 54 px, fond `--orange`, texte noir 16 px gras, pleine largeur, collé en bas d'écran quand il valide une liste.
- **Badge « à faire »** : fond `--orange`, texte noir, 13 px gras (ex. « 2 à faire »).
- **Ligne de match** (`_match_card.html`, partagée par la page Pronos et l'accueil) : en haut l'heure en gras puis la compétition (12 px, `#4A4F5C`), à droite une pastille d'état (« À jouer » `#F6F7FB` ; « Ferme dans X h Y » sous 24 h `#FFF3E8` / `#7A3900` ; « Prono enregistré » `#D6F2E1` / `#0E5A33` ; « En direct » `#FDE3E1` / `#B42318` ; « Terminé », « Reporté », « Annulé », « Fermé » en gris), plus la pastille de points sur un match terminé ; grille `minmax(0, 1fr) auto minmax(0, 1fr)` : écusson 36 px + abréviation 14 px gras / nom 11 px tronqué | centre de 116 px (2 cases, ou score réel 20 px + « Ton prono : x – y », ou bouton « Connecte-toi pour pronostiquer ») | même chose à droite, inversée ; en bas, pour un match ouvert, barre de tendance des joueurs de 6 px (domicile `#111111`, nul `#C9CCD6`, extérieur `#FF7900`) et « 48 · 24 · 28 % », place gardée sous 5 pronos. Sans logo : pastille ronde aux initiales.
- **Case de score** : 44×44 px, Outfit 22 px, chiffres tabulaires ; vide : fond `#F6F7FB`, bordure 1 px `#D5D8E1` ; remplie : bordure orange 2 px, fond `#FFF3E8`. Le code gagnant/perdant/nul reste pour les scores affichés (résultats, historique).
- **Podium** : carte `--ink`. 1er en orange (marche + avatar, texte noir), 2e et 3e en `--ink-2`. Le joueur courant a un contour orange sur son avatar.
- **Carte score final** : carte `--ink`, score en 48 px coloré avec les variantes « on dark » ; bandeau orange « Ton prono : x – y, score exact ! +5 » si score exact.
- **Badges de points** (accueil, Ligues, Profil) : score exact = fond `#0E7A43` texte blanc ; bon résultat = fond `#D6F2E1` texte `#0E5A33` ; 0 point = fond `#FDE3E1` texte `#B42318`. Les valeurs affichées sont celles du barème réglé dans le back-office (5 / 3 par défaut).
- **Avatars** : initiales sur fond `--orange-soft`, texte `--orange-text` (en attendant les photos de profil).
- **Barre de navigation** : 5 onglets (Accueil `/`, Ligues `/leagues`, Pronos `/matches`, Classements `/leaderboard`, Profil `/profile`), fond blanc, bordure haute `#E7E9F0`, icônes trait 2 px ; actif : icône `#FF7900` et libellé gras `#111111`, inactifs `#4A4F5C`. Affichée seulement pour un joueur connecté. Un visiteur ne voit que les pages publiques (accueil visiteur, connexion, inscription, pages légales), avec à la place un en-tête simple : logo (lien vers `/`) et langue FR · EN (`_guest_header.html`). `/results` n'a plus d'onglet (lien « Mes résultats d'hier » de l'accueil).
- **Écussons** : logos d'équipes fournis par API-Football (mis en cache), 36–44 px ; à défaut, initiales.

## 6. Écrans de référence
1. **Accueil** (la maquette `F-accueil.png` « Ma ligue » est remplacée) :
   - *visiteur* : héro noir (titre 34 px, « Jouer gratuitement », « J'ai déjà un compte », ballon en filigrane `#23262E`), « Comment ça marche » en 3 cartes numérotées, « À pronostiquer » (3 prochains matchs ouverts), carte orange « Compétition du moment », pied de page blanc ;
   - *joueur* : logo + avatar 36 px, « Salut [pseudo] » et la veille, 3 mini-cartes (ma ligue principale, points, réussite), bloc « Pronos à faire » à bordure orange 2 px avec les cartes de match et « Valider mes pronos », « Mes résultats d'hier », carrousel « Mes ligues » (cartes de 200 px, dernière en pointillés), « Chez les copains », prochain badge.
2. **Pronos** (`/matches`) : en-tête blanc (titre 26 px, pastille « N à faire »), rangée de pastilles de compétition qui défile (emblème 28 px ou code court, nom, compteur ; active noire, emblème et compteur orange), sélecteur « À jouer / Mes pronos / Tous », matchs par jour dans une carte blanche (filet `#E7E9F0`), barre fixe « N matchs sans prono » + bouton orange « Valider » (128 × 48) au-dessus de la barre de navigation, carte vide « Aucun match ici ».
3. **Match clôturé** : score final, résultat de mon prono, pronos de tous les membres de la ligue avec leurs points.
