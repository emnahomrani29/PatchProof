# État du projet et ce qu'il reste à faire

Point de situation du socle livré et des travaux restants, pour organiser la suite.

## Ce qui est construit et vérifié

Backend complet (49 tests au vert, `ruff` sans erreur) et frontend qui compile.
Vérifié sur le vrai stack `docker compose up` : import d'un projet → installation → tests
existants au vert → Bandit + Semgrep dans le bac à sable → alerte normalisée et affichée.
Un appel réel aux agents a aussi été validé via OpenRouter (Claude Sonnet 5.5).

| Module | État | Détail |
|---|---|---|
| Socle | ✅ | config, BD, schémas, client LLM (masquage, retries, validation), boucle d'agent, outils |
| M1 Comptes et projets | ✅ | auth, rôles, GitHub OAuth, import GitHub + ZIP, détection du framework, admin |
| M2 Détection | ✅ | Bandit + Semgrep, normalisation, fusion des doublons, filtrage des 4 familles, priorisation |
| M3 Agent Attaquant | ✅ code | runner + chargement du prompt + few-shot ; **à éprouver sur une vraie faille** |
| M4 Agent Défenseur | ✅ code | runner + auto-correction + diff relu depuis git ; **à éprouver sur une vraie faille** |
| M5 Validation / orchestration | ✅ | bac à sable Docker, validation 3 conditions + anti-triche, orchestrateur, limites, reprise |
| M6 Suivi / rapport / livraison | ✅ | suivi WebSocket, rapport JSON + PDF, patch, pull request GitHub, revue humaine |
| Frontend | ✅ | connexion, projets, import, analyse en direct, détail d'une faille, rapport, revue, admin |

## Ce qu'il reste à faire

### 1. Application de démonstration — bloquant pour la démo des agents
`demo-app/` n'a pas encore son `app.py`. C'est l'application Flask volontairement vulnérable
qui sert de cible : 4 vraies failles (une par famille), 2 faux positifs, ~10 tests existants.
Spécification complète : [demo.md](demo.md). Tant qu'elle n'existe pas, on ne peut pas filmer
la phase « faille confirmée puis corrigée » (tout ce qui précède, jusqu'à la détection, est déjà démontrable).

- [ ] `demo-app/app.py` (ou paquet) avec les 4 failles et les 2 faux positifs
- [ ] `demo-app/tests/` : une dizaine de tests du comportement normal, tous au vert
- [ ] `demo-app/ATTENDU.md` (réservé à l'équipe, hors dépôt) : verdict attendu par alerte
- [ ] Publier `demo-app/` comme dépôt GitHub public séparé (la démo commence par son import)

### 2. Prompts et exemples few-shot
Les agents tournent avec un prompt par défaut intégré. Pour de meilleurs résultats, écrire les
fichiers versionnés (chargés automatiquement s'ils existent) :

- [ ] `prompts/attaquant/systeme.md` et `prompts/defenseur/systeme.md`
- [ ] `prompts/exemples/cwe-89|78|798|22/attaque.md` et `correctif.md` (un exemple par famille)
- [ ] Tenir `prompts/CHANGELOG.md` à chaque modification (support de la présentation des prompts)

### 3. Validation de bout en bout sur la demo-app
Une fois 1 et 2 prêts :

- [ ] Lancer une analyse complète et vérifier : 4 corrigées, 2 faux positifs, 0 test cassé
- [ ] Mesurer les indicateurs de [demo.md](demo.md) §3 (coût, durée, taux)
- [ ] Ajuster les prompts selon les traces, puis refaire une mesure

### 4. Captures et vidéo pour la soutenance
- [ ] Captures d'écran de chaque étape (import, détection, suivi en direct, détail, rapport, PR)
- [ ] Vidéo de secours de la démonstration complète
- [ ] Vérifier que l'analyse pré-enregistrée est rejouable dans l'application

### 5. Finitions avant remise
- [ ] Renseigner les noms des membres dans [modules.md](modules.md) et l'organisation GitHub dans [CONTRIBUTING.md](../CONTRIBUTING.md)
- [ ] GitHub OAuth : créer l'app OAuth et remplir `GITHUB_CLIENT_ID` / `GITHUB_CLIENT_SECRET` dans `.env` (sinon import ZIP et patch téléchargeable suffisent)
- [ ] Tester `docker compose up` sur une machine propre
- [ ] Rédiger le rapport technique à partir de `docs/`

## Pour lancer le projet en local

```bash
cp .env.example .env         # renseigner OPENROUTER_API_KEY (déjà fait sur le poste de dev)
docker compose build
docker compose up
```

- Interface : http://localhost:5173
- API : http://localhost:8000/docs
- Le premier compte créé est administrateur.

## Tests et qualité

```bash
cd backend && pip install -e ".[dev]" && pytest          # 49 tests
cd backend && ruff check patchproof                      # style
cd frontend && npm install && npm run lint && npm run build
```
