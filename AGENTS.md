# AGENTS.md — PatchProof

Instructions pour tout agent IA (Claude Code, Cursor, Copilot…) qui travaille sur ce dépôt.
**Lis ce fichier en entier avant d'agir.**

PatchProof confie à deux agents IA la correction des vulnérabilités d'un projet web Python :
un agent **Attaquant** prouve chaque alerte par un test, un agent **Défenseur** la corrige, et le
correctif n'est accepté que si les tests le prouvent. Mini-projet *IA for Software Engineering* (5SAE).

---

## ÉTAPE 0 — OBLIGATOIRE : demande d'abord qui est l'utilisateur

**Avant toute autre action, pose la question :**

> « Quel membre de l'équipe es-tu ? »

et attends la réponse. Chaque membre est responsable d'UN module et ne travaille que sur ce module.
Tant que tu ne sais pas qui est l'utilisateur, **ne modifie aucun fichier et ne fais aucun commit.**

| Si l'utilisateur est… | Son module | Dossiers où il travaille |
|---|---|---|
| **Iheb Jlassi** | Socle (déjà poussé) **+ M3 Agent Attaquant** | `backend/patchproof/agents/attaquant/`, `prompts/attaquant/`, `prompts/exemples/*/attaque.md` |
| **Salma Louhichi** | M1 – Comptes et projets | `backend/patchproof/comptes/`, `frontend/src/pages/comptes/`, `frontend/src/pages/projets/` |
| **Abdel Kader Kaddachi** | M2 – Détection | `backend/patchproof/detection/`, `sandbox/regles/`, `frontend/src/pages/alertes/` |
| **Emna Homrani** | M4 – Agent Défenseur | `backend/patchproof/agents/defenseur/`, `prompts/defenseur/`, `prompts/exemples/*/correctif.md` |
| **Dhia Dine Bahi** | M5 – Validation et orchestration | `backend/patchproof/{sandbox,validation,orchestration}/`, `sandbox/Dockerfile` |
| **Yosser Khaldi** | M6 – Suivi, rapport et livraison | `backend/patchproof/{suivi,rapport,livraison}/`, `frontend/src/pages/{analyse,rapport,revue}/` |

La répartition complète et les interfaces publiques entre modules sont dans
[docs/modules.md](docs/modules.md). Le **socle** (configuration, base de données, client LLM, boucle
d'agent, outils, gabarit frontend) est déjà construit et poussé par Iheb : on s'appuie dessus, on n'y
touche pas sans prévenir le groupe (voir [CONTRIBUTING.md](CONTRIBUTING.md) §5).

---

## ÉTAPE 1 — Configurer Git au nom du membre (une seule fois)

La note est individuelle et pondérée par les commits : **chaque membre committe depuis son propre
compte**, sinon le travail ne lui est pas attribué.

```bash
git config user.name  "Prénom Nom"
git config user.email "adresse-du-compte-github@exemple.com"   # l'e-mail du compte GitHub du membre
```

Si le dépôt n'a pas encore de remote (tu travailles depuis le ZIP) :

```bash
git remote add origin https://github.com/<organisation>/patchproof.git   # URL partagée par Iheb
git fetch origin && git checkout main && git pull
```

**Ne jamais committer `.env`** (clés API) ni les dossiers `.venv/`, `node_modules/`, `data/`.

---

## ÉTAPE 2 — Travailler sur son module

1. Partir de `main` à jour, créer une branche nommée `m<N>/<sujet-court>` :
   ```bash
   git switch main && git pull
   git switch -c m3/boucle-attaquant        # exemple pour M3
   ```
2. Ne modifier **que les dossiers de son module** (tableau ci-dessus). Pour un fichier commun (socle,
   `docs/api.md`, `docs/modele-donnees.md`), prévenir le groupe et passer par une branche `socle/…`.
3. Écrire aussi ses tests dans `backend/tests/<module>/`.
4. Vérifier avant de pousser :
   ```bash
   cd backend && pip install -e ".[dev]" && pytest && ruff check patchproof
   cd frontend && npm install && npm run lint && npm run build
   ```

---

## ÉTAPE 3 — Committer et pousser

Format de message : `type(portée): description à l'infinitif` (voir [CONTRIBUTING.md](CONTRIBUTING.md) §3).

```bash
git add -A
git commit -m "feat(attaquant): prouver l'injection SQL par un test"
git push -u origin m3/boucle-attaquant
```

Puis ouvrir une **pull request** vers `main` sur GitHub, relue par un autre membre avant la fusion
(fusion par *merge commit*, pas de *squash*, pour garder les commits individuels).

- **Committe souvent, par petites étapes qui fonctionnent** (un gros commit final ne reflète pas le
  travail et pèse sur la note individuelle).
- Au moins une pull request par semaine.

---

## Lancer le projet en local

Prérequis : Docker Desktop lancé, une clé OpenRouter dans `.env`.

```bash
cp .env.example .env     # puis renseigner OPENROUTER_API_KEY
docker compose build && docker compose up
```

- Interface : http://localhost:5173 · API : http://localhost:8000/docs
- Le premier compte créé est administrateur.

## Où lire la suite

- [docs/README.md](docs/README.md) : index de la documentation (architecture, modules, API, agents…).
- [docs/etat-du-projet.md](docs/etat-du-projet.md) : ce qui est construit et ce qu'il reste à faire.
- [CONTRIBUTING.md](CONTRIBUTING.md) : branches, commits, pull requests, fichiers communs en détail.
- [docs/agents.md](docs/agents.md) : fonctionnement des agents (pour M3 et M4 surtout).

## Règles de travail

- Réponds à l'utilisateur en français ou dans sa langue.
- Les consignes des enseignants arrivent via le groupe ; si une exigence est ambiguë, le dire plutôt
  que deviner.
- Ne touche pas au module d'un autre membre sans accord explicite.
