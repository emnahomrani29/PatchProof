"""Choix de la commande d'installation des dépendances par le bac à sable (M5).

Régression : seul `requirements.txt` était pris en compte. Un projet déclarant ses dépendances dans
`pyproject.toml` ou `setup.py` — cas que la détection du framework accepte pourtant — s'exécutait
sans ses dépendances, et ses tests échouaient à tort dans le bac à sable.
"""

from pathlib import Path

from patchproof.sandbox.bac import BacASable


def bac(racine: Path) -> BacASable:
    """Instance sans conteneur : seule la racine du projet est utilisée par ces méthodes."""
    return BacASable(analyse_id=1, racine=racine, conteneur=None, client=None)


def test_requirements_txt(tmp_path):
    (tmp_path / "requirements.txt").write_text("flask\n", encoding="utf-8")
    assert bac(tmp_path)._commande_installation() == [
        "pip", "install", "--no-cache-dir", "--only-binary=:all:", "-r", "requirements.txt",
    ]


def test_pyproject_dependances_installees_sans_construire_le_projet(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        "[project]\nname = \"x\"\ndependencies = [\"fastapi>=0.115\", \"httpx\"]\n", encoding="utf-8")
    commande = bac(tmp_path)._commande_installation()
    assert commande[-2:] == ["fastapi>=0.115", "httpx"]
    assert "." not in commande  # on installe les dépendances, pas le projet lui-même


def test_pyproject_sans_dependances_declarees(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[project]\nname = \"x\"\n", encoding="utf-8")
    assert bac(tmp_path)._commande_installation() is None


def test_pyproject_illisible(tmp_path):
    (tmp_path / "pyproject.toml").write_text("ceci n'est pas du TOML [", encoding="utf-8")
    assert bac(tmp_path)._commande_installation() is None


def test_setup_py(tmp_path):
    (tmp_path / "setup.py").write_text("from setuptools import setup\n", encoding="utf-8")
    assert bac(tmp_path)._commande_installation()[-1] == "."


def test_requirements_txt_prioritaire(tmp_path):
    (tmp_path / "requirements.txt").write_text("flask\n", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text("[project]\nname = \"x\"\n", encoding="utf-8")
    assert bac(tmp_path)._commande_installation()[-2:] == ["-r", "requirements.txt"]


def test_projet_sans_fichier_de_dependances(tmp_path):
    assert bac(tmp_path)._commande_installation() is None
