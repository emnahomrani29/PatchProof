# PatchProof

PatchProof confie à deux agents IA la correction des vulnérabilités d'un projet web Python :
un agent **Attaquant** prouve chaque alerte par un test, un agent **Défenseur** la corrige,
et le correctif n'est accepté que si les tests le prouvent.

Mini-projet du module *IA for Software Engineering* (5SAE).

## Principe

1. Une faille n'est retenue que si un test la reproduit.
2. Un correctif n'est accepté que si ce test échoue désormais **et** si tous les tests existants passent encore.
3. Le test reste dans le projet comme test de non-régression.

Ce sont les tests, et non le LLM, qui jugent le résultat.

## Périmètre v1

- Projets Python web (Flask, FastAPI) avec tests pytest, < 5 000 lignes.
- Quatre familles : CWE-89, CWE-78, CWE-798, CWE-22.
- Import depuis un dépôt GitHub public ou une archive ZIP.
- Livraison en patch téléchargeable ou en pull request GitHub.

## Démarrage rapide

Prérequis : Docker Desktop lancé, une clé OpenRouter.

```bash
cp .env.example .env        # puis renseigner OPENROUTER_API_KEY
docker compose build
docker compose up
```

- Interface : http://localhost:5173
- API (documentation OpenAPI) : http://localhost:8000/docs

## Organisation du dépôt

| Dossier | Contenu |
|---|---|
| `backend/` | API FastAPI et worker d'analyse (un seul paquet Python `patchproof`) |
| `frontend/` | Interface React + Vite |
| `sandbox/` | Image Docker du bac à sable (Python, pytest, Bandit, Semgrep) |
| `prompts/` | Prompts système et exemples few-shot des agents, versionnés |
| `demo-app/` | Application Flask de démonstration utilisée en soutenance |
| `docs/` | Documentation : architecture, modules, API, données, agents, sécurité |

## Documentation

Commencer par [docs/README.md](docs/README.md).

Pour contribuer : [CONTRIBUTING.md](CONTRIBUTING.md) (branches, commits, pull requests).
