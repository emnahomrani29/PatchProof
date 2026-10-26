"""Module M2 — Détection des alertes brutes et priorisation (E-2.1, E-2.2).

Responsable : Abdel Kader Kaddachi.
"""

from patchproof.detection.familles import famille_bandit, famille_semgrep
from patchproof.detection.priorisation import fusionner, prioriser
from patchproof.detection.scanners import lancer_scanners

__all__ = [
    "famille_bandit",
    "famille_semgrep",
    "fusionner",
    "lancer_scanners",
    "prioriser",
]
