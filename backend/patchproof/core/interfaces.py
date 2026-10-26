"""Interfaces partagées, pour que chaque module se teste avec des objets factices."""

from pathlib import Path
from typing import Protocol

from patchproof.core.schemas import ResultatCommande


class Bac(Protocol):
    """Ce que les autres modules attendent du bac à sable (implémentation : patchproof.sandbox, M5).

    `racine` est la copie de travail du projet côté worker : on peut la lire et la modifier,
    mais on n'y exécute jamais rien. Toute exécution passe par `executer`.
    """

    racine: Path

    def synchroniser(self) -> None: ...

    def executer(self, commande: list[str], delai: int = 120) -> ResultatCommande: ...
