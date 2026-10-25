# Application de démonstration

Petite application Flask utilisée comme projet analysé pendant la soutenance.
Exigences et contrôles : [docs/demo.md](../docs/demo.md).

> Contient volontairement des failles. Ne jamais la déployer ni l'exposer sur un réseau :
> elle s'exécute uniquement dans le bac à sable de PatchProof ou via le client de test Flask.

À fournir dans ce dossier :

- `app.py` (ou un paquet `app/`) : une dizaine de routes, base SQLite créée au démarrage ;
- `requirements.txt` ;
- `tests/` : environ 10 tests pytest du comportement normal, tous au vert.

Lancer les tests en local (environnement virtuel dédié) :

```bash
cd demo-app
python -m venv .venv && .venv/Scripts/activate   # Windows ; source .venv/bin/activate sous Linux/macOS
pip install -r requirements.txt pytest
pytest -q
```
