# Exemple few-shot — preuve d'une traversée de répertoire (CWE-22)

Exemple injecté dans le prompt de l'Attaquant lorsque l'alerte appartient à cette famille.

## Situation

Alerte Semgrep `path-traversal-open` sur une route qui ouvre un fichier désigné par la requête :

```python
@app.route("/download")
def telecharger():
    nom = request.args.get("fichier", "")
    with open(os.path.join(DOSSIER_DOCS, nom), encoding="utf-8") as fichier:
        return fichier.read()
```

## Démarche

1. **Point d'entrée** : `GET /download?fichier=`, paramètre de requête.
2. **Hypothèse** : le nom est joint au dossier des documents sans contrôle, donc un chemin relatif
   remontant d'un niveau permet de lire un fichier situé **hors** du dossier prévu.
3. **Preuve attendue** : viser un fichier connu, présent à côté du dossier des documents, et constater
   que son contenu est renvoyé par la route.

## Test de preuve

```python
from app import app


def test_un_fichier_hors_du_dossier_est_renvoye():
    client = app.test_client()
    # requirements.txt se trouve à la racine du projet, en dehors du dossier des documents.
    reponse = client.get("/download", query_string={"fichier": "../requirements.txt"})
    assert reponse.status_code == 200
    assert "flask" in reponse.data.decode()
```

## Résultat attendu

Le test **passe** tant que le nom peut remonter à travers le dossier. Il **échoue** dès que la lecture
passe par une fonction du framework qui refuse de sortir du dossier, ou dès que le nom est résolu
contre une liste de fichiers connus.

## Reconnaître un faux positif

Une route qui valide le nom avant de l'utiliser — appartenance à une liste blanche, correspondance
dans un dictionnaire de fichiers connus — est signalée par la règle mais **n'est pas exploitable** :

```python
@app.route("/docs/<nom>")
def document(nom):
    if nom not in DOCS_AUTORISES:      # nom validé : aucune remontée possible
        abort(404)
    with open(os.path.join(DOSSIER_DOCS, nom + ".txt"), encoding="utf-8") as fichier:
        return fichier.read()
```

Dans ce cas, la tentative ci-dessus échoue et le verdict est `faux_positif`, avec la justification
qui cite le contrôle.
