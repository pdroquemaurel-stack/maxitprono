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
- **Carte match (saisie)** : ligne compétition · heure + état (« Ferme dans 1 h 42 » en `--orange-text`, « Enregistré » en `--muted`) ; grille `nom domicile | 2 cases de score | nom extérieur` ; ligne des pourcentages « 1 x % · N x % · 2 x % ».
- **Case de score** : 44×48 px, Outfit 22 px, couleur, bordure et fond selon le code gagnant/perdant/nul, recalculés à chaque saisie.
- **Podium** : carte `--ink`. 1er en orange (marche + avatar, texte noir), 2e et 3e en `--ink-2`. Le joueur courant a un contour orange sur son avatar.
- **Carte score final** : carte `--ink`, score en 48 px coloré avec les variantes « on dark » ; bandeau orange « Ton prono : x – y, score exact ! +5 » si score exact.
- **Badges de points** : score exact = fond `--orange` texte noir ; bon vainqueur = fond `--orange-soft` texte `#7A3600` ; 0 point = fond `#F1F2F6` texte `--muted`.
- **Avatars** : initiales sur fond `--orange-soft`, texte `--orange-text` (en attendant les photos de profil).
- **Barre de navigation** : 5 onglets (Ma ligue, Pronos, Classements, Résultats, Profil), icônes trait 2 px, actif en `--orange-text`, inactifs en `--muted`.
- **Écussons** : logos d'équipes fournis par API-Football (mis en cache), 36–44 px ; à défaut, initiales.

## 6. Écrans de référence
1. **Accueil (Ma ligue)** : sélecteur de ligue, podium, carte « X matchs sans prono », fil d'activité de la ligue, bouton d'invitation WhatsApp (bordure orange pointillée).
2. **Pronos (saisie directe)** : liste des matchs de la journée avec cases de score, bouton « Enregistrer mes pronos ».
3. **Match clôturé** : score final, résultat de mon prono, pronos de tous les membres de la ligue avec leurs points.
