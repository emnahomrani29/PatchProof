# Planning

Calendrier du module : sujet en semaine 1, point d'avancement en semaine 3, remise et soutenance en semaine 7.
Cocher les cases au fil de l'eau (dans la pull request qui termine la tâche).

## Vue d'ensemble

| Semaine | Objectif (cahier) | Résultat attendu |
|---|---|---|
| 1 | Validation du sujet | Cahier des charges validé, dépôt Git créé |
| 2 | Socle technique | `demo-app/` écrite, import de projet, bac à sable Docker, scanners, alertes normalisées |
| 3 | Agent Attaquant (**point d'avancement**) | Boucle d'agent fonctionnelle, tests de preuve générés pour l'injection SQL |
| 4 | Agent Défenseur et validation | Correctif appliqué et validé de bout en bout sur une faille |
| 5 | Les 4 familles + interface | Few-shot par famille, suivi en direct, gestion des erreurs d'API |
| 6 | Rapport, pull request et tests | Rapport PDF, pull request GitHub, mesure des indicateurs, vidéo de secours |
| 7 | Remise et soutenance | Code final, rapport technique, présentation des prompts, démonstration |

## Tâches par module

Légende : `[x]` fait et vérifié · `[~]` code en place, reste à éprouver · `[ ]` à faire.
Vue d'ensemble de l'avancement : [etat-du-projet.md](etat-du-projet.md).

### Socle (premier lot)
- [x] Structure du dépôt, documentation, guide de contribution
- [x] `docker-compose.yml` : api, worker, frontend, redis, postgres
- [x] Configuration, base de données, modèles, schémas
- [x] Client LLM : masquage, délai, nouvelles tentatives, validation JSON
- [x] Boucle d'agent générique et outils
- [x] Squelette du frontend : routage, mise en page, client API

### Semaine 2
- [x] **Tous** : `demo-app/` (4 failles, 2 faux positifs, ~10 tests) et son dépôt GitHub public
- [x] **M1** : inscription, connexion, import GitHub et ZIP, détection du framework
- [x] **M2** : lancement de Bandit et Semgrep, normalisation
- [x] **M5** : `BacASable` (créer, installer, détacher le réseau, exécuter, détruire), image `sandbox/`
- [x] **M6** : publication des étapes (BD + Redis), WebSocket

### Semaine 3 – point d'avancement
- [x] **M1** : vérification des tests existants avant l'analyse, liste et historique des projets
- [x] **M2** : fusion des doublons, filtrage des 4 familles, priorisation, exclusion d'une alerte
- [x] **M3** : prompt Attaquant, test de preuve généré et exécuté
- [x] **M3** : few-shot CWE-89 (+ les 3 autres familles, avance sur la semaine 5)
- [x] **M5** : orchestrateur (enchaînement Attaquant → verdict)
- [x] **M6** : page de suivi en direct
- [ ] **Tous** : import de `demo-app/` et preuve de l'injection SQL observée en direct

### Semaine 4
- [x] **M4** : prompt Défenseur (+ les 4 exemples de correctif), diff appliqué, auto-correction après un échec
- [x] **M5** : validation en 3 conditions, refus des diffs qui touchent `tests/`
- [x] **M5** : limites (tentatives, appels d'outils, budget)
- [ ] **Tous** : premier passage de bout en bout sur la faille CWE-89 et mesure du coût (D-02)

### Semaine 5
- [x] **M3 / M4** : few-shot CWE-78, CWE-798, CWE-22
- [x] **M5** : reprise d'une analyse interrompue, pause sur erreur d'API
- [x] **M6** : états des failles en direct, détail d'une faille (test, diff, résultats)
- [x] **M1** : administration (comptes, limites, modèles)
- [ ] **Tous** : analyse complète de `demo-app/` (4 corrigées, 2 faux positifs) et réglage des prompts

### Semaine 6
- [x] **M6** : rapport et export PDF, patch téléchargeable, pull request GitHub, acceptation par correctif
- [x] **M6** : page de revue humaine
- [ ] **Tous** : mesure des indicateurs (5 analyses), vidéo de secours, analyse pré-enregistrée
- [ ] **Tous** : rapport technique (base : `docs/`) et présentation des prompts

### Semaine 7
- [ ] Gel du code, `docker compose up` testé sur une machine propre
- [ ] Répétition de la démonstration (15 min)
