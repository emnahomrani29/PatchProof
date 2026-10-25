# Décisions techniques

Chaque décision a un statut : **adoptée**, **à valider** (en attente de l'avis de l'équipe ou de l'enseignant) ou **remplacée**.
Toute nouvelle décision qui change un choix du cahier des charges s'ajoute ici.

## Points à valider

| # | Question | Qui tranche |
|---|---|---|
| D-01 | Passer par OpenRouter alors que le cahier indique « API Claude ou OpenAI » | Équipe, puis enseignant si besoin |
| D-02 | Choix des modèles par défaut et budget de jetons | Équipe, après mesure en semaine 4 |
| D-03 | Réseau autorisé pendant l'installation des dépendances | Équipe |

---

## D-01 – Accès aux LLM via OpenRouter — *à valider*

**Contexte.** Le cahier des charges prévoit l'« API Claude ou OpenAI avec appel d'outils ». L'équipe dispose d'une clé OpenRouter.

**Décision.** Un seul client compatible OpenAI (`openai` Python, `base_url=https://openrouter.ai/api/v1`), le modèle étant choisi par configuration.
OpenRouter donne accès aux modèles Claude et OpenAI avec appel d'outils, ce qui reste conforme à l'esprit du cahier.

**Conséquences.**
- Changer de modèle = changer une variable d'environnement, ce qui facilite les comparaisons pour le rapport.
- Un intermédiaire de plus reçoit le code : le masquage s'applique avant l'envoi, comme pour un appel direct.
- Le rapport technique doit mentionner OpenRouter dans la section « API et modèles utilisés ».

## D-02 – Modèles par défaut — *à valider*

| Rôle | Variable | Défaut | Prix (entrée / sortie, par million de jetons) |
|---|---|---|---|
| Attaquant | `MODELE_ATTAQUANT` | `anthropic/claude-sonnet-5.5` | 2 $ / 10 $ |
| Défenseur | `MODELE_DEFENSEUR` | `anthropic/claude-sonnet-5.5` | 2 $ / 10 $ |
| Étapes simples (résumés pour le suivi) | `MODELE_LEGER` | `anthropic/claude-haiku-5.5` | 0,10 $ / 0,50 $ |

Critères : appel d'outils et sortie structurée supportés, bon niveau en Python et en sécurité, coût compatible avec l'objectif de moins de 2 $ par analyse.
Le budget par défaut de 400 000 jetons par analyse plafonne le coût d'entrée à environ 0,80 $.
**À mesurer en semaine 4** sur `demo-app/` : si le budget ne suffit pas pour 6 alertes, ou si le coût dépasse 2 $, comparer avec un modèle moins cher
(ex. `deepseek/deepseek-v4-pro`, `google/gemini-3.5-flash`) et consigner la comparaison ici et dans le rapport.

## D-03 – Réseau du bac à sable pendant l'installation — *à valider*

**Contexte.** Le cahier exige que le bac à sable n'ait aucun accès réseau sortant, mais il faut aussi vérifier que le projet s'installe (E-1.2), ce qui suppose de télécharger ses dépendances.

**Options.**
1. *(retenue)* Le conteneur est créé avec réseau, installe les dépendances avec `pip install --only-binary=:all:` (aucun script d'installation n'est exécuté), puis il est **détaché du réseau** avant toute exécution du code du projet (tests, scanners, agents).
2. Image préparée à l'avance avec les dépendances de `demo-app/`, sans réseau du tout : plus strict, mais seule l'application de démonstration serait analysable.
3. Proxy PyPI en liste blanche : plus propre, mais trop coûteux pour 7 semaines.

**Conséquence.** L'exigence « accès réseau sortant bloqué à 100 % » est vérifiée **pendant l'exécution du code analysé**, et c'est ainsi qu'il faut la formuler dans le rapport.

## D-04 – Un seul paquet Python pour l'API et le worker — *adoptée*

Même code, même image Docker, deux commandes (`uvicorn` et `rq worker`). Les modèles, la configuration et les schémas ne sont écrits qu'une fois.

## D-05 – Boucle d'agent écrite à la main — *adoptée*

Pas de LangChain ni de framework d'agents (cahier : « boucle d'agent maîtrisée, sans framework lourd »).
Environ 150 lignes dans `agents/boucle.py`, faciles à expliquer à l'oral et à tracer.

## D-06 – Schéma de base créé au démarrage — *adoptée*

`Base.metadata.create_all()` au lancement de l'API. Pas d'Alembic tant que le schéma évolue chaque semaine.
En cas de changement de table en développement : `docker compose down -v` pour repartir d'une base vide.

## D-07 – Règles Semgrep embarquées — *adoptée*

Le bac à sable n'a pas de réseau pendant l'analyse, alors que Semgrep télécharge normalement ses règles.
Les règles Python du registre sont téléchargées **au moment de la construction de l'image** (`sandbox/regles/`), et Semgrep est lancé avec `--metrics=off`.

## D-08 – Convention du test de preuve — *adoptée*

Le test de preuve **passe** tant que la faille est exploitable et **échoue** quand elle est corrigée.
Le cahier dit la même chose avec d'autres mots : « faille confirmée si le test d'exploitation réussit » puis « il doit maintenant échouer ».

## D-09 – Frontend en TypeScript — *adoptée*

React + Vite (cahier) en TypeScript : les types des réponses de l'API sont écrits une fois dans `frontend/src/api/types.ts`.

## D-10 – Alertes traitées une par une — *adoptée*

Un seul worker RQ et une seule alerte à la fois (cahier, E-5.3). Le parallélisme est hors périmètre de la v1.
