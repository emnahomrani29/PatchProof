# Exemple few-shot — correctif d'un secret codé en dur (CWE-798)

Exemple injecté dans le prompt du Défenseur lorsque la faille appartient à cette famille.

## Contexte

Faille confirmée : un jeton réel est écrit en clair dans le code source. Le code d'origine :

```python
# Jeton utilisé par les scripts de synchronisation internes.
API_TOKEN = "sk_demo_9f4b7c21e8a34d5f6b0c1e2d3a4b5c6d"
```

## Correctif minimal (diff unifié)

```diff
--- a/app.py
+++ b/app.py
@@ -18,5 +18,5 @@
 
 # Jeton utilisé par les scripts de synchronisation internes.
-API_TOKEN = "sk_demo_9f4b7c21e8a34d5f6b0c1e2d3a4b5c6d"
+API_TOKEN = os.environ.get("API_TOKEN", "")
 
 # Rapports disponibles dans le dossier des documents publics.
```

## Pourquoi il est accepté

1. **Test de preuve** : le module n'expose plus aucun secret en clair, le test qui constatait la
   présence du littéral échoue.
2. **Tests existants** : la valeur absente donne une chaîne vide ; l'application continue de
   fonctionner, et une variable d'environnement fournie rétablit le comportement complet.
3. **Alerte disparue** : plus aucun littéral n'est affecté à un nom de secret, la règle `B105` ne
   s'applique plus.

## Le piège à éviter

```python
API_TOKEN = os.environ["API_TOKEN"]   # à ne pas faire
```

Cette forme lève une exception **à l'import du module** lorsque la variable n'est pas définie : tous
les tests échouent d'un coup, la 2e condition n'est plus satisfaite et le correctif est refusé. Une
valeur de repli explicite (`os.environ.get(..., "")`) garde le module importable.

## À éviter également

- Déplacer le secret dans un autre fichier du dépôt (`.json`, `.ini`, constante dans un module) :
  il reste en clair dans le code livré.
- Chiffrer ou encoder la valeur en dur dans le source : la règle se déclenche toujours et la
  protection est illusoire.
- Ajouter une dépendance de gestion de secrets : elle ne serait pas installable sans réseau.
