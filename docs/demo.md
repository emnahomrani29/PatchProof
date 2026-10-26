# Démonstration

15 minutes en direct, sur une petite application Flask volontairement vulnérable préparée par l'équipe.

## 1. Application de démonstration (`demo-app/`)

Travail commun, à terminer en **semaine 2** : tous les modules s'en servent pour leurs tests.

Exigences :

| Élément | Attendu |
|---|---|
| Framework | Flask, une dizaine de routes, base SQLite créée au démarrage |
| Failles réelles | 4, une par famille : CWE-89, CWE-78, CWE-798, CWE-22 |
| Faux positifs | 2 alertes signalées par Bandit ou Semgrep **dans les 4 familles** (sinon le filtre de M2 les écarte avant les agents), mais réellement non exploitables |
| Tests existants | Environ 10 tests pytest qui passent, couvrant le comportement normal des routes |
| Taille | Quelques centaines de lignes |
| Dépôt | Publié aussi comme **dépôt GitHub public séparé**, puisque la démonstration commence par son import |

Contrôles avant la soutenance :

- `bandit -r .` et `semgrep` signalent bien 6 alertes après le filtrage de M2.
- Les tests existants passent avant l'analyse et après l'application des 4 correctifs.
- Chaque faille réelle est corrigeable par un changement minimal qui ne casse aucun test existant
  (sinon le Défenseur ne peut pas réussir, et c'est la démonstration qui échoue).
- Un fichier `ATTENDU.md`, réservé à l'équipe et absent du dépôt public, liste pour chaque alerte le verdict attendu.
  Il sert à mesurer les indicateurs de la section 3.

## 2. Déroulé (cahier des charges, section 11)

| # | Étape | Écran | Durée |
|---|---|---|---|
| 1 | Import du dépôt GitHub : Flask détecté, tests existants au vert | Nouveau projet | 1 min |
| 2 | Les scanners remontent 6 alertes classées par gravité | Sélection des alertes | 1 min |
| 3 | L'Attaquant prouve l'injection SQL par un test | Suivi en direct | 3 min |
| 4 | Le Défenseur passe à une requête paramétrée, et la validation montre le test de preuve en échec et les tests existants au vert | Suivi en direct, détail de la faille | 3 min |
| 5 | Une alerte est classée faux positif après 3 tentatives, avec sa justification | Détail de la faille | 2 min |
| 6 | Rapport final : 4 corrigées, 2 faux positifs, 0 test cassé, export PDF | Rapport | 2 min |
| 7 | Ouverture de la pull request GitHub | GitHub | 1 min |

Plan B :

- **Vidéo de secours** enregistrée en semaine 6.
- **Analyse pré-enregistrée** consultable dans l'application (suivi rejoué depuis la table `etapes_agent`) en cas de panne réseau ou d'API.

## 3. Mesure des indicateurs

À mesurer en semaine 6 sur 5 analyses de `demo-app/`, et à reporter dans le rapport technique.

| Indicateur | Cible | Mesure |
|---|---|---|
| Faux positifs correctement écartés | 80 % | verdicts `faux_positif` conformes à `ATTENDU.md` |
| Failles réelles reproduites par un test | 90 % | verdicts `confirmee` conformes |
| Failles prouvées corrigées automatiquement | 75 % | état `corrigee` / confirmées |
| Tests existants cassés par un correctif accepté | 0 | relancer les tests existants après le patch complet |
| Correctifs livrés avec leur test | 100 % | contenu du patch |
| Durée d'analyse | < 10 min | `termine_le - cree_le` |
| Coût d'une analyse | < 2 $ | `cout_estime_usd`, vérifié sur le tableau de bord OpenRouter |
