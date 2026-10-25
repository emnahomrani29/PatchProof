# Exemple few-shot — correctif d'une traversée de répertoire (CWE-22)

Exemple injecté dans le prompt du Défenseur lorsque la faille appartient à cette famille.

## Contexte

Faille confirmée par un test de preuve qui obtient le contenu d'un fichier situé hors du dossier des
documents. Le code d'origine :

```python
@app.route("/download")
def telecharger():
    nom = request.args.get("fichier", "")
    with open(os.path.join(DOSSIER_DOCS, nom), encoding="utf-8") as fichier:
        return fichier.read()
```

## Correctif minimal (diff unifié, deux blocs)

```diff
--- a/app.py
+++ b/app.py
@@ -8,7 +8,7 @@
 import subprocess
 
-from flask import Flask, abort, g, jsonify, request
+from flask import Flask, abort, g, jsonify, request, send_from_directory
 
 app = Flask(__name__)
@@ -113,8 +113,7 @@
 @app.route("/download")
 def telecharger():
     """Renvoie le contenu d'un document public du dossier des documents."""
     nom = request.args.get("fichier", "")
-    with open(os.path.join(DOSSIER_DOCS, nom), encoding="utf-8") as fichier:
-        return fichier.read()
+    return send_from_directory(DOSSIER_DOCS, nom)
 
 @app.route("/docs/<nom>")
```

## Pourquoi il est accepté

1. **Test de preuve** : `send_from_directory` refuse un chemin qui sort du dossier indiqué, la
   tentative de remontée ne renvoie plus le fichier visé.
2. **Tests existants** : la lecture d'un document légitime (`fichier=cgu.txt`) renvoie toujours son
   contenu, le contrat de la route est conservé.
3. **Alerte disparue** : la règle vise l'ouverture `open(...)` d'une valeur issue de la requête ; le
   code ne contient plus cette construction.

## Le piège à éviter absolument

```python
if nom not in DOCS_AUTORISES:
    abort(404)
with open(os.path.join(DOSSIER_DOCS, nom), encoding="utf-8") as fichier:   # alerte toujours là
    return fichier.read()
```

Cette validation **bloque bien l'attaque** — c'est un correctif de sécurité valable — mais la règle du
scanner est purement syntaxique : elle ne tient pas compte de la vérification qui précède, et l'alerte
reste signalée. La 3e condition échoue, le correctif est refusé. Il faut supprimer la forme de code
visée : ne plus appeler `open()` sur une valeur venue de la requête.

## Autres pistes acceptables

- Résoudre le chemin puis vérifier qu'il reste bien sous le dossier autorisé, **à condition** de ne
  plus passer la valeur de la requête directement à `open()` (par exemple en lisant via un fichier
  intermédiaire désigné par un dictionnaire de noms connus et une variable locale dérivée d'un
  littéral).
- Passer par `abort(404)` pour tout nom inconnu, en gardant le format de réponse existant.
