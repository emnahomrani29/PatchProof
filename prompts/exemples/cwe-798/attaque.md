# Exemple few-shot — preuve d'un secret codé en dur (CWE-798)

Exemple injecté dans le prompt de l'Attaquant lorsque l'alerte appartient à cette famille.

## Situation

Alerte `B105` sur une valeur secrète écrite en clair dans le code source :

```python
# Jeton utilisé par les scripts de synchronisation internes.
API_TOKEN = "sk_demo_9f4b7c21e8a34d5f6b0c1e2d3a4b5c6d"
```

## Démarche

1. **Constater** : le secret est attribué à une variable dont le nom annonce un jeton
   (`token`, `secret`, `password`, `key`…), et sa valeur est un littéral présent dans le fichier.
2. **Hypothèse** : quiconque lit le dépôt — ou un historique Git, un journal de construction, une
   archive livrée — dispose de la valeur réelle. Aucune exploitation réseau n'est nécessaire : la
   divulgation a déjà eu lieu.
3. **Preuve attendue** : importer la valeur depuis le module et constater qu'elle est bien un secret
   **utilisable** : non vide, de la forme attendue, de longueur plausible. Le test doit échouer dès
   que la valeur vient de l'environnement et n'est plus écrite dans le code.

## Test de preuve

```python
from app import API_TOKEN


def test_le_jeton_est_present_en_clair_dans_le_code():
    # Un secret écrit dans le source est lisible par toute personne ayant accès au dépôt.
    assert API_TOKEN.startswith("sk_")
    assert len(API_TOKEN) >= 32
```

## Résultat attendu

Le test **passe** tant que le littéral est dans le fichier. Il **échoue** quand la valeur est lue
dans l'environnement : le module n'expose alors plus aucun secret en clair.

## Distinguer un vrai secret d'un faux positif

Une alerte de cette famille est un **faux positif** lorsque la valeur signalée ne donne accès à rien :
texte de remplacement (`"a-configurer"`), valeur d'exemple dans un jeu de test, nom de variable
trompeur sans contenu secret. Dans ce cas, la tentative de preuve ci-dessus échoue et le verdict est
`faux_positif`.
