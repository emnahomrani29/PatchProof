# Exemple few-shot — preuve d'une injection SQL (CWE-89)

Exemple injecté dans le prompt de l'Attaquant lorsque l'alerte appartient à cette famille.

## Situation

Alerte Bandit `B608` sur une route qui construit sa requête par concaténation :

```python
@app.route("/users/search")
def chercher_utilisateur():
    nom = request.args.get("nom", "")
    lignes = connexion().execute(
        "SELECT id, nom, email FROM utilisateurs WHERE nom = '" + nom + "'"
    ).fetchall()
    return jsonify([dict(ligne) for ligne in lignes])
```

## Démarche

1. **Point d'entrée** : `GET /users/search?nom=`, paramètre de requête.
2. **Hypothèse** : la valeur est insérée telle quelle dans le texte de la requête, donc la condition
   `WHERE` peut être neutralisée et renvoyer des lignes que la recherche ne devrait pas laisser passer.
3. **Preuve attendue** : interroger la route avec une valeur qui rend la condition toujours vraie, et
   constater que la réponse contient **plus d'une ligne** — ce qu'une recherche sur un nom unique ne
   peut pas produire.

## Test de preuve

```python
from app import app


def test_la_recherche_renvoie_des_lignes_non_filtrees():
    client = app.test_client()
    reponse = client.get("/users/search", query_string={"nom": "' OR '1'='1"})
    assert reponse.status_code == 200
    trouves = reponse.get_json()
    # La recherche porte sur un seul nom : obtenir plusieurs comptes prouve que la
    # condition WHERE a été neutralisée.
    assert len(trouves) > 1
```

## Résultat attendu

Le test **passe** tant que la concaténation est en place. Il **échoue** dès que la requête devient
paramétrée : la valeur est alors traitée comme une donnée et la comparaison ne renvoie plus qu'une
correspondance exacte.

## Ce qu'il ne faut pas faire

- `assert reponse.status_code == 200` seul : la route répond 200 dans tous les cas, cela ne prouve rien.
- Appeler `chercher_utilisateur()` directement : la preuve doit passer par la route, comme le ferait
  un utilisateur.
