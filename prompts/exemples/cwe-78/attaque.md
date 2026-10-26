# Exemple few-shot — preuve d'une injection de commandes (CWE-78)

Exemple injecté dans le prompt de l'Attaquant lorsque l'alerte appartient à cette famille.

## Situation

Alerte `B602` sur une route qui construit sa commande par concaténation et l'exécute dans un shell :

```python
@app.route("/ping")
def ping():
    hote = request.args.get("host", "127.0.0.1")
    return subprocess.check_output("ping -c 1 " + hote, shell=True)
```

## Démarche

1. **Point d'entrée** : `GET /ping?host=`, paramètre de requête.
2. **Hypothèse** : la valeur est concaténée dans une commande confiée à un shell, donc un séparateur
   de commandes permet de faire exécuter un second programme.
3. **Preuve attendue** : demander la commande normale suivie d'un second programme qui produit une
   sortie reconnaissable, et constater que cette sortie apparaît dans la réponse. Le test ne dépend
   pas de l'outil `ping` lui-même : la sortie du second programme suffit à démontrer l'exécution.

## Test de preuve

```python
from app import app


def test_un_second_programme_est_execute_par_le_shell():
    client = app.test_client()
    reponse = client.get("/ping", query_string={"host": "127.0.0.1; echo preuve-injection"})
    assert reponse.status_code == 200
    assert b"preuve-injection" in reponse.data
```

## Résultat attendu

Le test **passe** tant que `shell=True` est présent. Il **échoue** quand la commande est passée sous
forme de liste d'arguments : le séparateur n'est plus interprété, il devient un argument ordinaire du
programme.

## Ce qu'il ne faut pas faire

- Se contenter de vérifier le code de retour `200`.
- Utiliser la sortie de `ping` : l'outil peut être absent du bac à sable, la preuve doit porter sur un
  effet produit **par l'injection elle-même**.
