# Exemple few-shot — correctif d'une injection de commandes (CWE-78)

Exemple injecté dans le prompt du Défenseur lorsque la faille appartient à cette famille.

## Contexte

Faille confirmée par un test de preuve qui fait exécuter un second programme à travers un séparateur
de commandes. Le code d'origine :

```python
return subprocess.check_output("ping -c 1 " + hote, shell=True)
```

## Correctif minimal (diff unifié)

```diff
--- a/app.py
+++ b/app.py
@@ -105,6 +105,6 @@
 @app.route("/ping")
 def ping():
     """Diagnostic réseau : vérifie que l'hôte indiqué répond."""
     hote = request.args.get("host", "127.0.0.1")
-    return subprocess.check_output("ping -c 1 " + hote, shell=True)
+    return subprocess.check_output(["ping", "-c", "1", hote])
```

## Pourquoi il est accepté

1. **Test de preuve** : la commande n'est plus confiée à un shell, le séparateur devient un argument
   ordinaire de `ping` et le second programme n'est jamais exécuté.
2. **Tests existants** : aucun test existant n'appelle cette route ; le contrat de la route est
   inchangé (elle renvoie toujours la sortie brute de la commande).
3. **Alerte disparue** : sans `shell=True`, la règle `B602` ne s'applique plus. La correction ne
   déclenche pas d'alerte de remplacement.

## À éviter

- Conserver `shell=True` en filtrant des caractères dans l'entrée : le motif détecté reste présent,
  et la robustesse du filtre n'est pas démontrable.
- Supprimer la route ou désactiver le contrôle : le contrat de l'application doit être conservé.

## Remarque utile sur les outils de détection

Bandit produit aussi des **notes d'audit** sur les appels à `subprocess` (`B603` sans shell, `B607`
chemin partiel). Ce ne sont pas des constats de vulnérabilité : PatchProof ne les range dans aucune
des quatre familles et les ignore. Seule la règle réellement signalée compte pour la 3e condition.
