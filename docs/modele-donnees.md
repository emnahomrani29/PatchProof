# Modèle de données

PostgreSQL 16 avec SQLAlchemy 2. Les modèles sont dans `backend/patchproof/core/modeles.py`.
En v1, les tables sont créées au démarrage (`create_all`). Pas de migrations tant que le schéma bouge.

## Diagramme

```mermaid
erDiagram
    UTILISATEUR ||--o{ PROJET : possede
    PROJET ||--o{ ANALYSE : a
    ANALYSE ||--o{ FAILLE : contient
    ANALYSE ||--o{ ETAPE_AGENT : trace
    FAILLE ||--o| TEST_PREUVE : prouvee_par
    FAILLE ||--o{ CORRECTIF : tentatives
    FAILLE ||--o{ ETAPE_AGENT : trace

    UTILISATEUR {
        int id PK
        string email UK
        string nom
        string mot_de_passe_hash
        string role "developpeur | responsable_securite | administrateur"
        bool actif
        string github_jeton_chiffre "nullable"
    }
    PROJET {
        int id PK
        int proprietaire_id FK
        string nom
        string source "github | zip"
        string url_github "nullable"
        string commit_sha "nullable"
        string chemin_stockage
        string framework "flask | fastapi"
        string commande_test
        int nb_lignes
    }
    ANALYSE {
        int id PK
        int projet_id FK
        string etat
        int jetons_utilises
        float cout_estime_usd
        string message_erreur "nullable"
        json parametres "copie des limites au lancement"
    }
    FAILLE {
        int id PK
        int analyse_id FK
        string outils "bandit, semgrep ou les deux"
        string regle
        string fichier
        int ligne
        string cwe
        string famille "sqli | commande | secret | traversee"
        string gravite "haute | moyenne | basse"
        bool exposee "atteignable depuis une route"
        int priorite
        string extrait
        bool exclue
        string etat
        string point_entree "nullable"
        string justification "nullable"
        int tentatives_attaque
        int tentatives_defense
        string decision_revue "nullable"
        string commentaire_revue "nullable"
    }
    TEST_PREUVE {
        int id PK
        int faille_id FK
        string chemin "tests/security/..."
        text contenu
        text sortie
    }
    CORRECTIF {
        int id PK
        int faille_id FK
        int tentative
        text diff
        text explication
        bool valide
        json resultat_validation
        string decision "en_attente | accepte | rejete"
    }
    ETAPE_AGENT {
        int id PK
        int analyse_id FK
        int faille_id FK "nullable"
        string agent "attaquant | defenseur | orchestrateur"
        string nature
        text resume
        string outil "nullable"
        json arguments "nullable, masqués"
        text resultat "tronqué à 4 000 caractères"
        bool succes
        int jetons_entree
        int jetons_sortie
        datetime cree_le
    }
```

Les paramètres d'administration (`budget_jetons_analyse`, `max_tentatives_agent`, `max_appels_outils_faille`, modèles)
sont stockés dans une table `parametres` à une seule ligne, initialisée depuis `.env`.

## États d'une faille

```mermaid
stateDiagram-v2
    [*] --> en_attente: alerte normalisée
    en_attente --> en_cours: l'Attaquant commence
    en_cours --> faux_positif: 3 tentatives sans preuve
    en_cours --> confirmee: test de preuve réussi
    confirmee --> corrigee: correctif validé (3 conditions)
    confirmee --> revue_humaine: 3 correctifs refusés
    en_cours --> revue_humaine: limite d'appels d'outils atteinte
    faux_positif --> [*]
    corrigee --> [*]
    revue_humaine --> [*]: décision du responsable sécurité
```

Une faille marquée `exclue` par le développeur reste `en_attente` et n'est jamais traitée.

**Reprise** (E-5.3) : à la reprise d'une analyse, l'orchestrateur ne traite que les failles
`en_attente`, `en_cours` ou `confirmee`. Une faille `en_cours` repart de zéro, une faille `confirmee` repart au Défenseur
avec son test de preuve déjà enregistré.

## États d'une analyse

`en_attente` → `preparation` → `detection` → `selection` → `traitement` → `terminee`,
avec `en_pause` (erreur d'API, quota, budget) et `echec` (installation impossible, tests existants en échec).
Voir [architecture.md §4.2](architecture.md#42-cycle-de-vie-dune-analyse).
