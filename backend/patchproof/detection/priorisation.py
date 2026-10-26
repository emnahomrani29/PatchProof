"""Fusion des doublons, filtrage des 4 familles et priorisation des alertes (E-2.2)."""

import re
from pathlib import Path

from patchproof.core.schemas import Alerte

RANG_GRAVITE = {"haute": 0, "moyenne": 1, "basse": 2}
# Indices qu'un fichier est atteignable depuis une route web (exposition).
MOTIFS_ROUTE = re.compile(r"@(app|router|bp|blueprint)\.(route|get|post|put|delete|patch)|APIRouter\(")


def fusionner(alertes: list[Alerte]) -> list[Alerte]:
    """Regroupe les alertes signalées au même endroit par les deux scanners."""
    par_cle: dict[tuple[str, int, str], Alerte] = {}
    for alerte in alertes:
        cle = (alerte.fichier, alerte.ligne, alerte.famille or alerte.cwe or alerte.regle)
        existante = par_cle.get(cle)
        if existante is None:
            par_cle[cle] = alerte
        else:
            existante.outils = sorted(set(existante.outils) | set(alerte.outils))
            existante.cwe = existante.cwe or alerte.cwe
            existante.famille = existante.famille or alerte.famille
            if RANG_GRAVITE[alerte.gravite] < RANG_GRAVITE[existante.gravite]:
                existante.gravite = alerte.gravite
            if len(alerte.extrait) > len(existante.extrait):
                existante.extrait = alerte.extrait
    return list(par_cle.values())


def prioriser(alertes: list[Alerte], racine: Path) -> list[Alerte]:
    """Ne garde que les 4 familles, marque l'exposition, trie par gravité puis exposition."""
    exposes = _fichiers_exposes(racine)
    retenues = [a for a in alertes if a.famille is not None]
    for alerte in retenues:
        alerte.exposee = alerte.fichier in exposes
    retenues.sort(key=lambda a: (RANG_GRAVITE[a.gravite], not a.exposee, a.fichier, a.ligne))
    for rang, alerte in enumerate(retenues, 1):
        alerte.priorite = rang
    return retenues


def _fichiers_exposes(racine: Path) -> set[str]:
    exposes = set()
    for chemin in racine.rglob("*.py"):
        parties = chemin.relative_to(racine).parts
        if {".git", ".venv", "venv", "node_modules", "__pycache__"}.intersection(parties):
            continue
        try:
            if MOTIFS_ROUTE.search(chemin.read_text(encoding="utf-8", errors="replace")):
                exposes.add(chemin.relative_to(racine).as_posix())
        except OSError:
            continue
    return exposes
