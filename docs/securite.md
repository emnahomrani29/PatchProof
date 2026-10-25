# Sécurité et garde-fous

PatchProof exécute du code qu'il ne connaît pas et envoie du code à un service externe.
Ce document liste les garde-fous et l'endroit où chacun est implémenté.

## 1. Garde-fous exigés par le module

| Contrainte | Mise en œuvre | Code |
|---|---|---|
| Aucune donnée personnelle brute envoyée au LLM | Masquage avant chaque envoi : secrets détectés, e-mails, numéros de téléphone, clés et jetons remplacés par `<SECRET_1>`, `<EMAIL_1>`… La correspondance reste côté serveur pour réécrire les diffs | `llm/masquage.py` |
| Sortie validée avant affichage | Schéma Pydantic pour chaque réponse finale. Un diff n'est appliqué que s'il est syntaxiquement valide, et un correctif n'est accepté qu'après validation par les tests | `llm/client.py`, `agents/boucle.py`, `validation/` |
| Erreurs d'appel API | Délai de 60 s par appel et 3 nouvelles tentatives (1 s, 4 s, 16 s). Message clair si le quota est dépassé ou la clé absente, puis analyse mise en pause et reprenable | `llm/client.py`, `orchestration/` |
| Agent qui triche | Le Défenseur n'a pas l'outil d'écriture de test, `appliquer_diff` refuse `tests/`, et la validation compare l'empreinte de `tests/` avant et après | `agents/outils.py`, `validation/` |
| Coût maîtrisé | Budget de jetons par analyse, 30 appels d'outils par faille, modèle léger pour les étapes simples | `agents/boucle.py`, `orchestration/` |
| Injection de prompt via le projet analysé | Le code, les commentaires et les sorties de tests sont des **données**, jamais des instructions : le prompt système le dit explicitement, et les résultats d'outils sont délimités. L'impact reste limité par construction : outils restreints par rôle, bac à sable sans réseau, aucune écriture dans `tests/` pour le Défenseur, acceptation décidée par du code déterministe | `prompts/`, `agents/outils.py`, `validation/` |

### Masquage : détails

- Détection par expressions régulières (formats de clés connus : `sk-…`, `ghp_…`, `AKIA…`, JWT, clés privées PEM) et par l'entropie des littéraux affectés à des noms comme `password`, `secret`, `token` ou `api_key`.
- Les secrets codés en dur (CWE-798) sont justement ce que l'on cherche à corriger : l'agent voit `<SECRET_1>` à la place de la valeur, ce qui suffit pour raisonner et proposer une variable d'environnement.
- Tout texte envoyé au LLM passe par une seule fonction, `masquer()`, appelée dans `ClientLLM.discuter()`. Il n'existe pas d'autre chemin vers l'API.
- Test de non-régression : aucune valeur de la liste de secrets connus de `demo-app/` ne doit apparaître dans les requêtes enregistrées (indicateur « 0 secret en clair »).

## 2. Bac à sable

| Exigence | Mise en œuvre |
|---|---|
| Aucune exécution hors du bac à sable | Le worker n'importe et n'exécute jamais le code analysé. Toute commande passe par `BacASable.executer()` |
| Réseau sortant bloqué à 100 % | Le conteneur est détaché de tout réseau avant la première exécution du code du projet (voir D-03) |
| 2 Go de mémoire, 120 s | `mem_limit=2g`, `memswap_limit=2g`, `pids_limit=256`, commande enveloppée par `timeout 120` |
| Isolation entre analyses | Un conteneur par analyse, fichiers copiés par archive tar (pas de montage de l'hôte), supprimé à la fin |
| Privilèges | Utilisateur non root dans l'image, `cap_drop=ALL`, `no-new-privileges`, système de fichiers racine en lecture seule sauf `/projet` et `/tmp` |

Installation des dépendances : `pip install --only-binary=:all:` (paquets wheel uniquement, donc aucun script d'installation n'est exécuté),
seule étape avec réseau. Un projet qui exige une compilation depuis les sources est signalé comme non supporté en v1.

## 3. Sécurité de PatchProof lui-même

| Point | Mesure |
|---|---|
| Mots de passe | Hachage bcrypt |
| Sessions | Jeton JWT signé (HS256), expiration 12 h, secret dans `.env` |
| Jeton GitHub | Chiffré en base (Fernet, clé dans `.env`), portée `public_repo` |
| Import ZIP | Taille ≤ 20 Mo, refus des chemins absolus et des `..` (zip slip), refus des liens symboliques |
| Import GitHub | URL `https://github.com/<owner>/<repo>` uniquement, clonage `--depth 1` |
| Accès aux ressources | Chaque route vérifie que le projet appartient à l'utilisateur (sauf rôles responsable sécurité et administrateur) |
| Socket Docker | Monté uniquement dans le worker, jamais dans l'API ni dans le bac à sable |
| Secrets de configuration | Uniquement dans `.env` (ignoré par Git) ; `.env.example` contient des valeurs factices |

## 4. Données de l'application de démonstration

`demo-app/` contient volontairement des failles. Elle ne doit jamais être déployée ni exposée sur un réseau :
on l'utilise uniquement comme projet analysé, dans le bac à sable ou via son client de test.
