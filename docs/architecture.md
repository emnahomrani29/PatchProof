# Architecture

Structure inspirée d'arc42 : contexte, composants (boîte noire puis boîte blanche), exécution, déploiement.
Les diagrammes sont en Mermaid (rendus directement par GitHub).

## 1. Objectifs et contraintes

| Priorité | Objectif de qualité | Conséquence sur l'architecture |
|---|---|---|
| 1 | **Sécurité** : le code analysé ne s'exécute jamais hors du bac à sable | Conteneur Docker isolé par analyse, sans réseau à l'exécution |
| 2 | **Fiabilité** : un correctif accepté ne casse aucun test | Validation déterministe en 3 conditions, faite par du code et non par le LLM |
| 3 | **Traçabilité** : chaque décision d'agent est journalisée | Table `etapes_agent` remplie à chaque appel LLM et chaque appel d'outil |
| 4 | **Réactivité** : une analyse de plusieurs minutes ne bloque pas l'API | Worker séparé, file Redis, diffusion par WebSocket |

Contraintes : 7 semaines, 6 personnes, Python côté serveur, lancement en une commande (`docker compose up`).

## 2. Vue de contexte

PatchProof est ici vu comme une boîte noire, avec ses voisins et les données échangées.

```mermaid
flowchart LR
    dev([Développeur])
    rs([Responsable sécurité])
    adm([Administrateur])
    pp[[PatchProof]]
    llm[(API LLM<br/>OpenRouter)]
    gh[(GitHub)]

    dev -- "projet (URL / ZIP), acceptation des correctifs" --> pp
    pp -- "suivi en direct, rapport PDF, patch" --> dev
    rs -- "décisions de revue humaine" --> pp
    pp -- "failles en revue, historique" --> rs
    adm -- "comptes, limites, modèles" --> pp
    pp -- "prompts masqués + définitions d'outils" --> llm
    llm -- "appels d'outils, réponses JSON" --> pp
    pp -- "OAuth, clonage, pull request" --> gh
    gh -- "code source, URL de la PR" --> pp
```

Bandit, Semgrep et pytest ne sont pas des voisins : ils sont intégrés dans l'image du bac à sable.

## 3. Vue des composants

### 3.1 Niveau 1 (boîte blanche du système)

```mermaid
flowchart TB
    subgraph PatchProof
        ui[Interface web<br/>React + Vite]
        api[API<br/>FastAPI]
        redis[(Redis<br/>file + pub/sub)]
        worker[Worker d'analyse<br/>RQ]
        db[(PostgreSQL)]
        sb[Bac à sable<br/>conteneur Docker par analyse]
    end
    llm[(API LLM)]
    gh[(GitHub)]

    ui -- "REST / JSON" --> api
    api -- "WebSocket : étapes en direct" --> ui
    api -- "enfile une analyse" --> redis
    redis -- "tâche" --> worker
    worker -- "publie les étapes" --> redis
    redis -- "abonnement" --> api
    api <--> db
    worker <--> db
    worker -- "API Docker : exécuter, copier" --> sb
    worker -- "HTTPS" --> llm
    worker -- "HTTPS" --> gh
    api -- "OAuth" --> gh
```

| Composant | Responsabilité | Interfaces fournies |
|---|---|---|
| Interface web | Soumettre un projet, suivre les agents, relire et accepter les correctifs, consulter le rapport | Pages web |
| API | Authentification, projets, création d'analyses, diffusion du suivi | REST `/api/*`, WebSocket `/ws/analyses/{id}` ([api.md](api.md)) |
| Redis | File des analyses en attente et canal des étapes | File RQ `analyses`, canal `analyse:{id}` |
| Worker | Orchestrateur déterministe et boucles des deux agents | Tâche `lancer_analyse(analyse_id)` |
| Bac à sable | Installer le projet, lancer les scanners et les tests | Commandes exécutées via l'API Docker |
| PostgreSQL | Projets, analyses, failles, tests, correctifs, traces | Schéma ([modele-donnees.md](modele-donnees.md)) |

### 3.2 Niveau 2 (paquet Python `patchproof`)

L'API et le worker partagent le même paquet Python et la même image Docker : seule la commande de lancement change.

```mermaid
flowchart TB
    subgraph socle
        core[core<br/>config, BD, modèles, schémas]
        llmc[llm<br/>client OpenRouter, masquage,<br/>retries, validation JSON]
        apim[api<br/>application FastAPI]
    end
    comptes[comptes<br/>M1]
    detection[detection<br/>M2]
    att[agents.attaquant<br/>M3]
    def[agents.defenseur<br/>M4]
    sandbox[sandbox<br/>M5]
    valid[validation<br/>M5]
    orch[orchestration<br/>M5]
    suivi[suivi<br/>M6]
    rapport[rapport<br/>M6]
    livraison[livraison<br/>M6]

    apim --> comptes & detection & suivi & rapport & livraison
    orch --> detection & att & def & valid & suivi
    att & def --> llmc
    att & def & valid & detection --> sandbox
    comptes & detection & att & def & valid & orch & suivi & rapport & livraison --> core
```

Règle de dépendance : les modules dépendent du socle et des interfaces publiques des autres modules
(les fonctions listées dans [modules.md](modules.md)), jamais de leurs détails internes.
Seul `orchestration` enchaîne les modules entre eux.

## 4. Vue d'exécution

### 4.1 Traitement d'une alerte

```mermaid
sequenceDiagram
    participant O as Orchestrateur
    participant A as Agent Attaquant
    participant D as Agent Défenseur
    participant V as Validation
    participant S as Bac à sable
    participant DB as PostgreSQL

    O->>DB: faille.etat = en_cours
    loop jusqu'à 3 tentatives
        O->>A: analyser(alerte)
        A->>S: lire, chercher, écrire test, exécuter test
        A-->>O: verdict JSON (confirmee / faux_positif)
    end
    alt faux positif
        O->>DB: faille.etat = faux_positif (+ justification)
    else confirmée
        O->>DB: faille.etat = confirmee (+ test de preuve)
        loop jusqu'à 3 tentatives
            O->>D: corriger(faille, test, dernier échec)
            D->>S: lire, chercher, appliquer diff
            D-->>O: diff JSON
            O->>V: valider(diff)
            V->>S: test de preuve, tests existants, scanner
            V-->>O: résultat (3 conditions)
        end
        alt les 3 conditions sont remplies
            O->>DB: faille.etat = corrigee (+ correctif)
        else 3 échecs
            O->>DB: faille.etat = revue_humaine
        end
    end
    Note over O,DB: Chaque étape est enregistrée puis publiée sur Redis pour le suivi en direct
```

Le détail de la boucle d'un agent (appels d'outils, limites) est dans [agents.md](agents.md).

### 4.2 Cycle de vie d'une analyse

```mermaid
stateDiagram-v2
    [*] --> en_attente: POST /api/projets/{id}/analyses
    en_attente --> preparation: le worker prend la tâche
    preparation --> echec: installation ou tests existants KO
    preparation --> detection
    detection --> selection: alertes normalisées et classées
    selection --> traitement: le développeur valide la liste
    traitement --> en_pause: erreur d'API, quota ou budget
    en_pause --> traitement: reprise (failles déjà traitées conservées)
    traitement --> terminee: toutes les alertes traitées
    terminee --> [*]
```

`selection` correspond à l'exigence E-2.2 : le développeur peut exclure une alerte avant le passage des agents.

## 5. Vue de déploiement

```mermaid
flowchart TB
    subgraph hote["Poste hôte : Docker Desktop"]
        subgraph compose["docker compose"]
            fe["frontend<br/>node:22, Vite :5173"]
            be["api<br/>image patchproof-backend<br/>uvicorn :8000"]
            wk["worker<br/>image patchproof-backend<br/>rq worker"]
            rd["redis:7 :6379"]
            pg["postgres:16 :5432<br/>volume pgdata"]
        end
        sb1["patchproof-sandbox<br/>(1 par analyse)<br/>réseau coupé, 2 Go, 120 s/commande"]
        dk[["démon Docker"]]
    end
    llm[(openrouter.ai)]
    gh[(github.com)]

    fe -- "HTTP / WS" --> be
    be -- "TCP" --> rd & pg
    wk -- "TCP" --> rd & pg
    wk -- "socket Docker" --> dk
    dk -- "crée / supprime" --> sb1
    wk -- "HTTPS" --> llm & gh
```

- Le worker pilote le démon Docker de l'hôte (socket monté) pour créer les conteneurs du bac à sable.
- Les fichiers du projet sont copiés dans le conteneur (archive tar) et non montés depuis l'hôte, ce qui isole les analyses entre elles.
- Le conteneur n'a accès au réseau que pendant l'installation des dépendances. Il est détaché du réseau avant toute exécution du code du projet (voir [decisions.md](decisions.md), D-03).

## 6. Concepts transverses

| Concept | Où | Résumé |
|---|---|---|
| Garde-fous LLM | `llm/` | Masquage avant envoi, schéma JSON, délai de 60 s et 3 nouvelles tentatives ([securite.md](securite.md)) |
| Traces | `core/`, `suivi/` | Chaque étape d'agent est enregistrée en base puis publiée sur Redis |
| Configuration | `core/config.py` | Variables d'environnement uniquement (`.env`), aucune clé dans le code |
| Reprise | `orchestration/` | Les failles déjà dans un état final ne sont pas retraitées |
| Extensibilité | `detection/`, `prompts/exemples/` | Ajouter une famille = une règle de filtrage + un exemple few-shot, sans toucher aux agents |
