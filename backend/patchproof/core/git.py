"""Appels Git sur l'espace de travail d'un projet, sans jamais exécuter de code du projet.

Les options forcées désactivent tout ce qui pourrait lancer une commande définie par le dépôt
(hooks, fsmonitor, filtres). Un dossier .git provenant d'une archive ZIP est supprimé à l'import.
"""

import subprocess
from pathlib import Path

_OPTIONS_SURES = [
    "-c", "core.hooksPath=/dev/null",
    "-c", "core.fsmonitor=false",
    "-c", "protocol.file.allow=never",
    "-c", "user.name=PatchProof",
    "-c", "user.email=patchproof@localhost",
]


class ErreurGit(Exception):
    pass


def git(racine: Path, *args: str, entree: str | None = None, verifier: bool = True) -> str:
    resultat = subprocess.run(
        ["git", *_OPTIONS_SURES, *args],
        cwd=racine,
        input=entree,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    if verifier and resultat.returncode != 0:
        raise ErreurGit((resultat.stderr or resultat.stdout).strip())
    return resultat.stdout


def initialiser_depot(racine: Path) -> str:
    """Crée le commit de base si besoin, et renvoie son SHA."""
    if not (racine / ".git").exists():
        git(racine, "init", "-q")
    git(racine, "add", "-A")
    if git(racine, "status", "--porcelain"):
        git(racine, "commit", "-q", "-m", "Base PatchProof")
    return git(racine, "rev-parse", "HEAD").strip()


def diff_depuis(racine: Path, reference: str = "HEAD", *chemins: str) -> str:
    git(racine, "add", "-A", "--intent-to-add")
    return git(racine, "diff", reference, "--", *chemins)


def revenir_a(racine: Path, reference: str = "HEAD") -> None:
    git(racine, "reset", "-q", "--hard", reference)
    git(racine, "clean", "-q", "-fd")


def valider(racine: Path, message: str) -> str:
    git(racine, "add", "-A")
    git(racine, "commit", "-q", "--allow-empty", "-m", message)
    return git(racine, "rev-parse", "HEAD").strip()
