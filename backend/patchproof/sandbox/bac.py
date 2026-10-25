"""Bac à sable : un conteneur Docker par analyse (docs/securite.md §2, docs/decisions.md D-03).

Le worker garde une copie de travail du projet sur disque (lue et modifiée par les outils des
agents) et la synchronise dans le conteneur avant chaque exécution. Le code analysé ne s'exécute
jamais côté worker : seule `executer()` lance des commandes, et uniquement dans le conteneur.
"""

import io
import logging
import tarfile
import time
from pathlib import Path

import docker
from docker.errors import DockerException, NotFound

from patchproof.core.config import parametres
from patchproof.core.schemas import ResultatCommande

journal = logging.getLogger("patchproof.sandbox")

RACINE_CONTENEUR = "/projet"
DOSSIERS_EXCLUS = {".git", ".venv", "venv", "node_modules", "__pycache__", ".pytest_cache", ".mypy_cache"}


class ErreurBac(Exception):
    pass


class BacASable:
    """Cycle de vie : creer -> installer -> (synchroniser -> executer)* -> detruire."""

    def __init__(self, analyse_id: int, racine: Path, conteneur, client):
        self.analyse_id = analyse_id
        self.racine = racine
        self._conteneur = conteneur
        self._client = client
        self._reseau_coupe = False

    # -- création ---------------------------------------------------------------

    @classmethod
    def creer(cls, analyse_id: int, racine: Path) -> "BacASable":
        p = parametres()
        try:
            client = docker.from_env()
        except DockerException as e:
            raise ErreurBac("Docker est injoignable. Est-ce que Docker Desktop est lancé ?") from e

        conteneur = client.containers.run(
            p.image_sandbox,
            command=["sleep", "infinity"],
            detach=True,
            name=f"patchproof-bac-{analyse_id}-{int(time.time())}",
            network_mode="bridge",          # réseau pour l'installation, coupé ensuite
            mem_limit=p.memoire_sandbox,
            memswap_limit=p.memoire_sandbox,
            pids_limit=256,
            cap_drop=["ALL"],
            security_opt=["no-new-privileges"],
            working_dir=RACINE_CONTENEUR,
            labels={"patchproof": "bac", "analyse": str(analyse_id)},
        )
        bac = cls(analyse_id, racine, conteneur, client)
        bac._copier_vers_conteneur()
        return bac

    # -- transfert de fichiers --------------------------------------------------

    def _archive(self) -> bytes:
        flux = io.BytesIO()
        with tarfile.open(fileobj=flux, mode="w") as tar:
            for chemin in self.racine.rglob("*"):
                rel = chemin.relative_to(self.racine)
                if DOSSIERS_EXCLUS.intersection(rel.parts):
                    continue
                if chemin.is_file() or chemin.is_dir():
                    tar.add(chemin, arcname=rel.as_posix(), recursive=False)
        return flux.getvalue()

    def _copier_vers_conteneur(self) -> None:
        self._conteneur.exec_run(["mkdir", "-p", RACINE_CONTENEUR])
        if not self._conteneur.put_archive(RACINE_CONTENEUR, self._archive()):
            raise ErreurBac("Échec de la copie du projet dans le bac à sable.")

    def synchroniser(self) -> None:
        """Recopie l'état courant de la copie de travail dans le conteneur (après édition par un agent)."""
        self._copier_vers_conteneur()

    # -- exécution --------------------------------------------------------------

    def installer(self, commande: list[str] | None = None) -> ResultatCommande:
        """Installe les dépendances (seule étape avec réseau), puis coupe le réseau."""
        resultat = ResultatCommande(code_retour=0, sortie="aucune dépendance déclarée")
        req = self.racine / "requirements.txt"
        cmd = commande or (
            ["pip", "install", "--no-cache-dir", "--only-binary=:all:", "-r", "requirements.txt"]
            if req.is_file() else None
        )
        if cmd:
            resultat = self.executer(cmd, delai=300, avec_reseau=True)
        self._couper_reseau()
        return resultat

    def _couper_reseau(self) -> None:
        if self._reseau_coupe:
            return
        try:
            for nom in list(self._conteneur.attrs["NetworkSettings"]["Networks"]):
                self._client.networks.get(nom).disconnect(self._conteneur, force=True)
            self._reseau_coupe = True
            journal.info("Analyse %s : réseau du bac à sable coupé", self.analyse_id)
        except (DockerException, KeyError) as e:
            journal.warning("Analyse %s : impossible de couper le réseau (%s)", self.analyse_id, e)

    def executer(self, commande: list[str], delai: int | None = None, avec_reseau: bool = False) -> ResultatCommande:
        if not avec_reseau:
            self._couper_reseau()
        delai = delai or parametres().delai_execution
        enveloppe = ["timeout", "--signal=KILL", str(delai), *commande]
        try:
            res = self._conteneur.exec_run(enveloppe, workdir=RACINE_CONTENEUR, demux=False)
        except DockerException as e:
            raise ErreurBac(f"Échec d'exécution dans le bac à sable : {e}") from e
        sortie = res.output.decode("utf-8", errors="replace") if res.output else ""
        # 124 : code de sortie de `timeout` quand le délai est dépassé.
        if res.exit_code == 124 or res.exit_code == 137:
            return ResultatCommande(code_retour=res.exit_code, sortie=sortie, delai_depasse=True)
        return ResultatCommande(code_retour=res.exit_code, sortie=sortie)

    # -- destruction ------------------------------------------------------------

    def detruire(self) -> None:
        try:
            self._conteneur.remove(force=True)
        except NotFound:
            pass
        except DockerException as e:
            journal.warning("Analyse %s : conteneur non supprimé (%s)", self.analyse_id, e)

    def __enter__(self) -> "BacASable":  # noqa: PYI034
        return self

    def __exit__(self, *_exc) -> None:
        self.detruire()
