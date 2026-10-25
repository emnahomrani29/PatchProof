"""Import d'un projet (GitHub public ou ZIP) et détection du framework (E-1.2)."""

import io
import re
import shutil
import subprocess
import zipfile
from pathlib import Path

from patchproof.core.config import parametres
from patchproof.core.erreurs import Invalide
from patchproof.core.git import initialiser_depot
from patchproof.core.schemas import InfoProjet

TAILLE_MAX_ZIP = 20 * 1024 * 1024
DOSSIERS_IGNORES = {".git", ".venv", "venv", "node_modules", "__pycache__"}


def dossier_projet(projet_id: int) -> Path:
    return parametres().dossier_projets / str(projet_id)


def cloner_github(url: str, cible: Path) -> str:
    if not re.fullmatch(r"https://github\.com/[\w.-]+/[\w.-]+/?", url):
        raise Invalide("URL GitHub invalide : https://github.com/<proprietaire>/<depot> attendu.")
    cible.parent.mkdir(parents=True, exist_ok=True)
    res = subprocess.run(
        ["git", "-c", "core.hooksPath=/dev/null", "clone", "--depth", "1", "--quiet", url.rstrip("/"), str(cible)],
        capture_output=True, text=True, timeout=120, check=False,
    )
    if res.returncode != 0:
        raise Invalide(f"Clonage impossible : {res.stderr.strip()[:300]}", code="import_github")
    return initialiser_depot(cible)


def extraire_zip(contenu: bytes, cible: Path) -> str:
    if len(contenu) > TAILLE_MAX_ZIP:
        raise Invalide("Archive trop volumineuse (20 Mo au plus).", code="zip_trop_gros")
    try:
        archive = zipfile.ZipFile(io.BytesIO(contenu))
    except zipfile.BadZipFile as e:
        raise Invalide("Fichier ZIP illisible.", code="zip_invalide") from e

    cible.mkdir(parents=True, exist_ok=True)
    racine = cible.resolve()
    for info in archive.infolist():
        nom = info.filename
        if nom.startswith(("/", "\\")) or ".." in Path(nom).parts:
            raise Invalide(f"Chemin refusé dans l'archive : {nom}", code="zip_invalide")
        if (info.external_attr >> 16) & 0o170000 == 0o120000:
            raise Invalide(f"Lien symbolique refusé dans l'archive : {nom}", code="zip_invalide")
        destination = (cible / nom).resolve()
        if not destination.is_relative_to(racine):
            raise Invalide(f"Chemin refusé dans l'archive : {nom}", code="zip_invalide")
        if info.is_dir():
            destination.mkdir(parents=True, exist_ok=True)
        else:
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(archive.read(info))

    _remonter_dossier_unique(cible)
    # Un .git venu d'une archive pourrait contenir une configuration exécutable : on repart de zéro.
    shutil.rmtree(cible / ".git", ignore_errors=True)
    return initialiser_depot(cible)


def _remonter_dossier_unique(cible: Path) -> None:
    """Une archive qui contient un seul dossier racine (projet-main/) est aplatie."""
    entrees = [e for e in cible.iterdir() if e.name not in {"__MACOSX"}]
    if len(entrees) == 1 and entrees[0].is_dir():
        unique = entrees[0]
        for element in list(unique.iterdir()):
            shutil.move(str(element), str(cible / element.name))
        unique.rmdir()


def fichiers_python(racine: Path):
    for chemin in racine.rglob("*.py"):
        if not DOSSIERS_IGNORES.intersection(chemin.relative_to(racine).parts):
            yield chemin


def detecter_framework(racine: Path) -> InfoProjet:
    texte_deps = ""
    for nom in ("requirements.txt", "pyproject.toml", "setup.py", "Pipfile"):
        if (racine / nom).is_file():
            texte_deps += (racine / nom).read_text(encoding="utf-8", errors="replace").lower()

    nb_lignes, imports = 0, ""
    for chemin in fichiers_python(racine):
        contenu = chemin.read_text(encoding="utf-8", errors="replace")
        nb_lignes += contenu.count("\n") + 1
        imports += "\n".join(l for l in contenu.splitlines() if l.lstrip().startswith(("import ", "from ")))

    framework = None
    if "fastapi" in texte_deps or re.search(r"^\s*(from|import)\s+fastapi", imports, re.MULTILINE):
        framework = "fastapi"
    elif "flask" in texte_deps or re.search(r"^\s*(from|import)\s+flask", imports, re.MULTILINE):
        framework = "flask"

    a_des_tests = any(
        p.name.startswith("test_") or p.name.endswith("_test.py") for p in fichiers_python(racine)
    )
    return InfoProjet(framework=framework, nb_lignes=nb_lignes, a_des_tests=a_des_tests)
