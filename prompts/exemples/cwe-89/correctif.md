# Exemple few-shot — correctif d'une injection SQL (CWE-89)

Exemple injecté dans le prompt du Défenseur lorsque la faille appartient à cette famille.

## Contexte

Faille confirmée par un test de preuve qui obtient plusieurs lignes en neutralisant la condition
`WHERE`. Le code d'origine :

```python
lignes = connexion().execute(
    "SELECT id, nom, email FROM utilisateurs WHERE nom = '" + nom + "'"
).fetchall()
```

## Correctif minimal (diff unifié)

```diff
--- a/app.py
+++ b/app.py
@@ -88,7 +88,7 @@
 @app.route("/users/search")
 def chercher_utilisateur():
     nom = request.args.get("nom", "")
     lignes = connexion().execute(
-        "SELECT id, nom, email FROM utilisateurs WHERE nom = '" + nom + "'"
-    ).fetchall()
+        "SELECT id, nom, email FROM utilisateurs WHERE nom = ?", (nom,)
+    ).fetchall()
     return jsonify([dict(ligne) for ligne in lignes])
```

## Pourquoi il est accepté

1. **Test de preuve** : la valeur est désormais liée à un paramètre, `' OR '1'='1` est comparé
   littéralement au champ `nom` et ne renvoie plus qu'une correspondance exacte ou aucune ligne.
2. **Tests existants** : la recherche normale (`nom=alice`) renvoie toujours la même ligne.
3. **Alerte disparue** : le texte SQL redevient un littéral non formaté, la règle `B608` ne s'applique
   plus.

## À éviter

- Construire la requête avec `.format()` ou une f-string : le motif détecté reste présent.
- Échapper les guillemets à la main ou filtrer certains caractères : fragile, et le scanner continue
  de signaler la concaténation.
- Réécrire la route, changer son contrat ou son format de réponse : le correctif doit rester minimal.
