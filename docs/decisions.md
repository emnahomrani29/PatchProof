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

## D-11 – Notes d'audit de Bandit écartées des familles — *adoptée*

**Contexte.** Bandit produit deux sortes de constats : ceux qui affirment une vulnérabilité (`B608`,
`B602`, `B105`…) et des **notes d'audit**, qui invitent à relire le code sans rien affirmer
(`B404` « import de subprocess », `B603` « subprocess sans shell », `B607` « chemin partiel »).
Ces trois dernières portent malgré tout le CWE-78, donc le repli « CWE → famille » les rangeait dans la
famille « injection de commandes ».

**Conséquences observées**, mesurées sur `demo-app/` :
- chaque appel à `subprocess` produisait une alerte supplémentaire, y compris sur du code correct ;
- surtout, un correctif remplaçant `shell=True` par une liste d'arguments faisait disparaître `B602`
  mais apparaître `B603` **à la même ligne** : la 3e condition de validation (« le scanner ne signale
  plus l'alerte ») échouait, donc **aucun correctif d'injection de commandes ne pouvait être accepté**.

**Décision.** `REGLES_BANDIT_AUDIT` dans `detection/familles.py` énumère ces règles : elles ne sont
rattachées à aucune famille, donc écartées par le filtrage de M2 et ignorées par la validation.
La famille d'une alerte Bandit vient d'abord de la règle ; le CWE ne sert que de repli pour une règle
inconnue.

**Conséquence.** Le périmètre ne contient plus que des constats de vulnérabilité. À dire dans le
rapport : le filtre est volontairement restrictif et une note d'audit n'est jamais présentée comme une
faille. Pour Semgrep, le nom de la règle fait de même foi que le CWE, car les métadonnées du registre
sont parfois imprécises (`tainted-sql-string` annonce CWE-704 alors qu'elle décrit une injection SQL).

## D-12 – Extrait de code relu dans le projet — *adoptée*

**Contexte.** L'agent Attaquant reçoit un court extrait de code pour chaque alerte. Bandit fournit un
snippet utilisable, mais le champ `lines` de Semgrep contient l'annotation de la règle et non le code :
sur les règles du paquet du registre, il vaut littéralement `requires login` pour **toutes** les alertes.

**Décision.** `detection/scanners.extrait_source()` relit le fichier du projet et renvoie les lignes
entourant l'alerte, numérotées comme l'outil `lire_fichier` (2 lignes de contexte de chaque côté).

**Conséquence.** L'extrait transmis au modèle est toujours fidèle et lisible directement. La lecture se
fait sur la copie de travail du worker, sans passer par le bac à sable.

## D-13 – Réflexion des modèles à raisonnement — *adoptée*

**Contexte.** Les modèles utilisés raisonnent : leur réflexion arrive dans un champ distinct du contenu
(`reasoning`, et `reasoning_details[].text` chez OpenRouter) tandis que `content` reste à `null` tant
qu'ils n'ont pas produit de réponse finale. Le client ne lisait que `content`.

**Conséquences observées**, sur une analyse réelle de `demo-app/` : un tour contenant uniquement du
raisonnement passait pour une réponse vide, sa réflexion était perdue, la boucle renvoyait deux fois de
plus la même demande puis abandonnait — l'alerte partait alors à tort en revue humaine. Le suivi en
direct n'affichait aucun raisonnement, alors que la démonstration doit justement les montrer.

**Décision.**
- `ReponseLLM.raisonnement` porte le texte de réflexion, démasqué comme le reste (voir D-14).
- La boucle publie une étape `raisonnement` à partir du contenu, ou de la réflexion quand il n'y a pas
  de contenu, et n'injecte **pas** un tour assistant vide dans l'historique : un message assistant sans
  contenu fait dérailler les appels suivants.
- Les prompts exigent que la réponse finale soit un message de texte (une réflexion interne ne compte
  pas) et que le raisonnement soit rédigé en français.

## D-14 – Le masquage couvre aussi la réflexion — *adoptée*

Le démasquage s'applique au contenu **et** au raisonnement : un extrait de code ou un secret recopié par
le modèle dans sa réflexion traverse le même masqueur que le reste de l'échange, et une même valeur
garde le même marqueur pendant toute l'analyse (voir [securite.md](securite.md)).

