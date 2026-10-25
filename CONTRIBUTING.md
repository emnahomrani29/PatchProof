# Guide de contribution

L'équipe compte 6 membres, et chacun est responsable d'un module (voir [docs/modules.md](docs/modules.md)).
**Chacun committe son propre travail, depuis son propre compte**, pour que l'historique montre qui a fait quoi.

## 1. Mise en place (une seule fois)

```bash
git clone https://github.com/<organisation>/patchproof.git
cd patchproof

# Identité : doit correspondre à votre compte GitHub, sinon vos commits ne vous sont pas attribués
git config user.name  "Prénom Nom"
git config user.email "adresse-du-compte-github@exemple.com"

cp .env.example .env    # ne jamais committer .env
```

Vérifier l'attribution : sur GitHub, l'avatar de chaque commit doit être le vôtre.
Si l'e-mail n'est pas reconnu, l'ajouter dans *GitHub → Settings → Emails*.

## 2. Branches

- `main` : toujours fonctionnelle. Personne ne pousse directement dessus.
- Une branche par tâche, créée depuis `main` à jour :

```bash
git switch main
git pull
git switch -c m2/normalisation-alertes
```

Nommage : `m<numéro du module>/<sujet-court>`. Exemples :

| Branche | Module |
|---|---|
| `m1/import-github` | 1 – Comptes et projets |
| `m2/fusion-doublons` | 2 – Détection |
| `m3/boucle-attaquant` | 3 – Agent Attaquant |
| `m4/auto-correction` | 4 – Agent Défenseur |
| `m5/bac-a-sable-docker` | 5 – Validation et orchestration |
| `m6/export-pdf` | 6 – Suivi, rapport et livraison |
| `socle/<sujet>` | Fichiers communs (voir §5) |

## 3. Messages de commit

Format : `type(portée): description à l'infinitif`

```
feat(detection): fusionner les alertes signalées par Bandit et Semgrep
fix(sandbox): appliquer la limite mémoire de 2 Go
test(attaquant): couvrir le cas des 3 tentatives infructueuses
docs(api): décrire le flux WebSocket du suivi en direct
```

| Type | Usage |
|---|---|
| `feat` | Nouvelle fonctionnalité |
| `fix` | Correction de bogue |
| `test` | Ajout ou modification de tests |
| `docs` | Documentation |
| `refactor` | Restructuration sans changement de comportement |
| `chore` | Configuration, dépendances, Docker |

Portées : `comptes`, `detection`, `attaquant`, `defenseur`, `sandbox`, `validation`, `orchestration`, `suivi`, `rapport`, `livraison`, `frontend`, `prompts`, `demo`, `socle`.

Règles :

- **Un commit = un changement cohérent.** Committez souvent, par petites étapes qui fonctionnent :
  les petits commits se relisent et s'annulent plus facilement qu'un seul gros.
- Description courte (< 72 caractères), en français, sans point final.
- Pas de fichiers générés, de `.env`, de clés API ni de dossiers `node_modules/`, `__pycache__/` ou `.venv/`.
- Lancer les tests de votre module avant chaque push (voir §6).

## 4. Pull requests

```bash
git push -u origin m2/normalisation-alertes
```

Ouvrir ensuite une pull request vers `main` sur GitHub :

- Titre au même format qu'un commit.
- Description : ce qui change, comment le tester, la capture d'écran si l'interface change.
- **Au moins une relecture** par un autre membre avant la fusion.
- Fusion par *merge commit* (pas de *squash*), pour conserver vos commits individuels dans l'historique.

Si `main` a avancé pendant votre travail :

```bash
git switch main && git pull
git switch m2/normalisation-alertes
git merge main          # résoudre les conflits, relancer les tests, puis pousser
```

## 5. Qui modifie quoi

Chaque module a ses dossiers (détail dans [docs/modules.md](docs/modules.md)).
On modifie librement ses propres dossiers.

Les **fichiers communs** (le socle) sont utilisés par tous :

- `backend/patchproof/core/` (configuration, base de données, modèles, schémas)
- `backend/patchproof/llm/` (client LLM et garde-fous)
- `backend/patchproof/agents/boucle.py` et `agents/outils.py` (boucle d'agent et outils)
- `backend/patchproof/api/`, `backend/patchproof/worker.py`, `docker-compose.yml`, `.env.example`
- `frontend/src/` hors `pages/` (gabarit, session, client API, styles)
- `docs/api.md`, `docs/modele-donnees.md`

Pour les modifier : prévenir le groupe, utiliser une branche `socle/...` et une pull request relue par le responsable concerné.
Tout changement d'un contrat (route d'API, table, format JSON) se reporte dans la documentation **dans la même pull request**.

## 6. Tests avant de pousser

```bash
# Backend
cd backend
pip install -e ".[dev]"
pytest tests/<votre_module>

# Frontend
cd frontend
npm install
npm run lint && npm run build
```

## 7. Ordre de démarrage

1. Le premier lot (structure, documentation, socle) est poussé sur `main`.
2. Chaque membre clone le dépôt, configure son identité (§1) et crée sa première branche.
3. Chacun développe son module et ouvre des pull requests régulières (au moins une par semaine).
