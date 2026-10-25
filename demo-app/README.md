# Application de démonstration

Petite application Flask utilisée comme projet analysé pendant la soutenance.
Exigences et contrôles : [docs/demo.md](../docs/demo.md).

> Contient volontairement des défauts de sécurité. Ne jamais la déployer ni l'exposer sur un réseau :
> elle s'exécute uniquement dans le bac à sable de PatchProof ou via le client de test Flask.

## Contenu

| Fichier | Rôle |
|---|---|
| `app.py` | 9 routes, base SQLite créée au premier démarrage (`demo.sqlite3`, non versionnée) |
| `tests/test_app.py` | 11 tests du comportement normal, tous au vert avant l'analyse |
| `docs_publics/` | Documents servis par les routes `/download` et `/docs/<nom>` |
| `requirements.txt` | Flask, seule dépendance |

Les alertes attendues, leur verdict et les correctifs attendus sont décrits dans `ATTENDU.md` :
ce fichier est réservé à l'équipe et n'est pas versionné.

## Lancer les tests en local

```bash
cd demo-app
python -m venv .venv && .venv/Scripts/activate   # Windows ; source .venv/bin/activate sous Linux/macOS
pip install -r requirements.txt pytest
pytest -q
```

Attendu : **10 réussis, 1 ignoré** sous Windows. Le test de la route `/report` est ignoré hors Linux
parce que cette route s'appuie sur `cat` ; il s'exécute normalement dans le bac à sable, qui est Linux.

## Publier la démonstration

La soutenance commence par l'import de ce dossier comme dépôt GitHub public distinct. À faire en
semaine 6, en vérifiant qu'`ATTENDU.md` n'est pas emporté (`git check-ignore demo-app/ATTENDU.md`).

