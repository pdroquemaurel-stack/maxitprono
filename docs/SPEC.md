# MaxitProno — Spécification du POC

À placer dans `docs/SPEC.md`. Source : réponses de Paul dans le document « Questions avant lancement ».

## 1. Objectif du POC
Prouver que le jeu fonctionne et engage, en web mobile autonome, avant l'intégration dans Max it.
- Pays pilotes : Cameroun, Burkina Faso (mais aucune séparation par pays dans le jeu).
- 100 % gratuit, sans paiement. Publicité et lots : plus tard.
- Langues : français (défaut) et anglais.
- Charte graphique propre au jeu (pas celle de Max it).

## 2. Compétitions
- Principales compétitions internationales (CAN, CAF, Ligue des champions UEFA, grands championnats européens).
- Championnats locaux des pays pilotes (Cameroun Elite One, championnat du Burkina Faso), si l'API les couvre.
- Toute la saison + événements ponctuels.
- L'admin choisit les compétitions actives dans le back-office.

## 3. Règles du jeu
- Pronostic : **score exact** uniquement.
- Clôture : **10 minutes avant** le coup d'envoi. Le joueur peut modifier son pronostic jusque-là.
- Points (paramétrables par l'admin) :
  - bon vainqueur ou bon match nul : X points (défaut : 3)
  - bonus score exact : Y points en plus (défaut : 2)
  - sinon : 0
- Match annulé : le pronostic est annulé (0 point, non compté). Match reporté : le pronostic reste valable pour la nouvelle date.
- Points calculés automatiquement quand le score final est disponible.

## 4. Probabilités affichées
Pour chaque match, afficher 3 pourcentages : **victoire équipe 1 / nul / victoire équipe 2**.
- Source à privilégier : endpoint `predictions` d'API-Football (pourcentages directs).
- Sinon : conversion des cotes en probabilités, normalisées pour que le total fasse 100 %.
- Ne pas afficher de nom de bookmaker ni de lien vers un site de paris.

## 5. Classements
- Général, par pays (pays déclaré par le joueur), par compétition, par semaine, par ligue privée.
- Départage : 1) points, 2) nombre de scores exacts, 3) nombre de bons vainqueurs, 4) date d'inscription la plus ancienne.

## 6. Ligues privées
- Création par un joueur, qui en devient admin.
- Code d'invitation, partageable par WhatsApp et réseaux sociaux (lien de partage).
- Taille max : 100 membres (paramétrable par l'admin global).
- Ouvertes à tous les pays.

## 7. Compte joueur
- Première connexion : pseudo, avatar (upload), pays, acceptation du règlement du jeu.
- POC : connexion par pseudo + code PIN. Plus tard : login Max it (identifiant crypté unique, lié au numéro).
- Pas de chat, pas de commentaires.

## 8. Écrans du MVP
1. Accueil : prochains matchs à pronostiquer, mon rang
2. Matchs : liste par compétition et par jour, avec pourcentages 1/N/2
3. Pronostic : saisie du score, modifiable jusqu'à la clôture
4. Classements : onglets général / pays / compétition / semaine
5. Ligues : mes ligues, créer, rejoindre par code, classement de la ligue
6. Profil : pseudo, avatar, pays, historique de mes pronostics
7. Règles du jeu
8. Page d'erreur réseau : message + bouton « réessayer »

## 9. Back-office admin
- Activer ou désactiver des compétitions
- Modifier le barème de points
- Corriger un score ou ajouter un match à la main
- Modifier la taille max des ligues
- Voir les KPIs de base : inscrits, joueurs actifs par semaine, pronostics par joueur, ligues créées

## 10. Données et technique
- L'API foot n'est appelée que par le back-end, via des tâches planifiées, et le résultat est stocké en base.
- Tâches : import des matchs à venir (1 fois par jour), mise à jour des scores (toutes les 5-10 min pendant les créneaux de match), calcul des points après chaque score final.
- Respecter le quota de l'offre API choisie (journaliser le nombre d'appels).

## 11. Plus tard (hors POC)
Badges et séries de victoires, lots, publicité, sponsors, notifications, arabe, intégration Max it (TCMPP web-view + wx.login).

## 12. Découpage en étapes pour Claude Code
1. Squelette du projet, configuration, base de données, page d'accueil vide, déploiement sur Render.
2. Client API-Football + import des compétitions et matchs + script de vérification de couverture.
3. Comptes joueurs (pseudo + PIN, profil, règlement).
4. Pronostics + règle de clôture (avec tests).
5. Calcul des points + classements + départage (avec tests).
6. Ligues privées + lien de partage.
7. Pourcentages 1/N/2.
8. Back-office admin + KPIs.
9. Traductions FR/EN, page d'erreur, finitions mobile.
