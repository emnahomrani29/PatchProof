# État du projet et ce qu'il reste à faire

Point de situation du socle livré et des travaux restants, pour organiser la suite.

## Ce qui est construit et vérifié

Backend complet (**84 tests** au vert, `ruff` sans erreur) et frontend qui compile.

Vérifié sur le vrai stack et avec le vrai modèle :

- `docker compose up` : import d'un projet → installation → tests existants au vert → Bandit + Semgrep
  dans le bac à sable → alertes normalisées et affichées ;
- la détection relève les **6 alertes attendues** sur `demo-app/` : 4 failles réelles et 2 faux positifs,
  tous dans les 4 familles ;
- l'agent **Attaquant** a réellement prouvé l'injection SQL de `demo-app/` (Claude Sonnet 5.5 via
  OpenRouter) : 15 étapes, 17 s, 0,08 $, test de preuve écrit puis exécuté, et re-vérifié ensuite par
  l'orchestrateur. Il a de lui-même réécrit un premier test qui ne prouvait rien ;
- les **4 correctifs minimaux** ont été appliqués sur une copie : les tests existants restent au vert et
  seules les 2 alertes fausses subsistent, donc chaque faille réelle est bien corrigeable.

| Module | État | Détail |
|---|---|---|
| Socle | ✅ | config, BD, schémas, client LLM (masquage, retries, validation), boucle d'agent, outils |
| M1 Comptes et projets | ✅ | auth, rôles, GitHub OAuth, import GitHub + ZIP, détection du framework, admin |
| M2 Détection | ✅ | Bandit + Semgrep, normalisation, fusion des doublons, filtrage des 4 familles, priorisation |
| M3 Agent Attaquant | ✅ | runner, prompt système, exemples few-shot ; reste à éprouver sur l'analyse complète |
| M4 Agent Défenseur | ✅ | runner, prompt système, exemples de correctif ; reste à éprouver sur l'analyse complète |
| M5 Validation / orchestration | ✅ | bac à sable Docker, validation 3 conditions + anti-triche, orchestrateur, limites, reprise |
| M6 Suivi / rapport / livraison | ✅ | suivi WebSocket, rapport JSON + PDF, patch, pull request GitHub, revue humaine |
| Frontend | ✅ | connexion, projets, import, analyse en direct, détail d'une faille, rapport, revue, admin |
| Application de démonstration | ✅ | 9 routes Flask + base SQLite, 4 failles réelles et 2 faux positifs relevés par les vrais scanners, 11 tests au vert |
| Prompts | ✅ | 2 prompts système et 8 exemples few-shot, versionnés dans `prompts/` |

## Ce qu'il reste à faire

### 1. Application de démonstration — fait et vérifié
`demo-app/app.py` (9 routes, base SQLite créée au démarrage) et `demo-app/tests/test_app.py`
(11 tests) sont en place. Les vrais scanners relèvent **6 alertes dans les 4 familles** : 4 failles
réelles et 2 faux positifs, conformément à `docs/demo.md`. Les 4 correctifs minimaux ont été appliqués
sur une copie : les tests existants restent au vert et seules les 2 alertes fausses subsistent.
La carte des verdicts est dans `demo-app/ATTENDU.md` (réservé à l'équipe, non versionné).

- [x] `demo-app/app.py` avec les 4 failles et les 2 faux positifs
- [x] `demo-app/tests/` : tests du comportement normal, tous au vert
- [x] `demo-app/ATTENDU.md` : verdict attendu et correctif attendu par alerte
- [ ] Publier `demo-app/` comme dépôt GitHub public séparé (la démonstration commence par son import)

### 2. Prompts et exemples few-shot — faits, à éprouver
- [x] `prompts/attaquant/systeme.md` et `prompts/defenseur/systeme.md`
- [x] `prompts/exemples/cwe-{89,78,798,22}/{attaque,correctif}.md` (8 exemples)
- [x] `prompts/CHANGELOG.md` amorcé
- [ ] Éprouver les prompts sur une analyse complète, puis remplir la colonne « Effet mesuré »

### 3. Validation de bout en bout sur la demo-app
Tout est prêt côté code et prompts ; il reste à lancer l'analyse et à la mesurer.

- [ ] Lancer une analyse complète et vérifier : 4 corrigées, 2 faux positifs, 0 test cassé
- [ ] Mesurer les indicateurs de [demo.md](demo.md) §3 sur 5 analyses (coût, durée, taux)
- [ ] Ajuster les prompts selon les traces, puis refaire une mesure

### 4. Captures et vidéo pour la soutenance
- [ ] Captures d'écran de chaque étape (import, détection, suivi en direct, détail, rapport, pull request)
- [ ] Vidéo de secours de la démonstration complète
- [ ] Vérifier que l'analyse pré-enregistrée est rejouable dans l'application

### 5. Finitions avant remise
- [ ] Renseigner la répartition des modules dans [modules.md](modules.md) (les six noms y figurent déjà) et l'organisation GitHub dans [CONTRIBUTING.md](../CONTRIBUTING.md)
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
cd backend && pip install -e ".[dev]" && pytest          # 84 tests
cd backend && ruff check patchproof                      # style
cd frontend && npm install && npm run lint && npm run build
```
