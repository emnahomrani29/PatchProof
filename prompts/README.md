# Prompts des agents

Chargés par le worker au lancement de chaque agent : une modification ici s'applique à l'analyse suivante, sans redémarrage.

| Fichier | Responsable | Contenu |
|---|---|---|
| `attaquant/systeme.md` | M3 | Rôle, méthode, règles, format de sortie de l'Attaquant |
| `defenseur/systeme.md` | M4 | Rôle, méthode, règles, format de sortie du Défenseur |
| `exemples/<cwe>/attaque.md` | M3 | Exemple few-shot : démarche de preuve pour la famille |
| `exemples/<cwe>/correctif.md` | M4 | Exemple few-shot : correctif minimal pour la famille |
| `CHANGELOG.md` | M3, M4 | Historique des versions des prompts et raison de chaque changement |

Dossiers d'exemples : `cwe-89` (injection SQL), `cwe-78` (injection de commandes), `cwe-798` (secrets codés en dur), `cwe-22` (traversée de répertoire).

Variables remplacées à l'exécution, notées `{{nom}}` : `{{alerte}}`, `{{extrait}}`, `{{exemple}}`, `{{test_preuve}}`, `{{echec_precedent}}`.

Techniques et format de sortie : voir [docs/agents.md](../docs/agents.md) §7.
