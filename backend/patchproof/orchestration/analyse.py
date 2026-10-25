"""Cycle de vie d'une analyse (tâche RQ exécutée par le worker).

preparation -> detection -> selection (attente du développeur) -> traitement -> terminee,
avec en_pause (quota/budget) et echec (installation ou tests existants KO). Reprenable.
"""

import logging
import shutil
from pathlib import Path

from patchproof.core.config import parametres
from patchproof.core.db import session
from patchproof.core.git import initialiser_depot
from patchproof.core.modeles import Analyse, EtatAnalyse, Faille, Famille, Projet, maintenant
from patchproof.core.schemas import Etape
from patchproof.detection.priorisation import fusionner, prioriser
from patchproof.detection.scanners import lancer_scanners
from patchproof.orchestration.orchestrateur import AnalyseEnPause, traiter_failles
from patchproof.sandbox.bac import BacASable, ErreurBac
from patchproof.suivi.publication import publier_etape, publier_etat_analyse

journal = logging.getLogger("patchproof.analyse")


def _information(analyse_id: int, resume: str, *, succes: bool = True) -> None:
    """Étape de progression hors agents (M6, suivi en direct).

    La préparation et la détection durent une à trois minutes sans produire d'étape d'agent : sans
    ces messages, l'interface n'a rien à afficher et paraît bloquée alors que l'analyse progresse.
    """
    publier_etape(Etape(analyse_id=analyse_id, agent="orchestrateur", nature="information",
                        resume=resume[:2000], succes=succes))


def _resume_tests(sortie: str) -> str:
    """Ligne de résumé de pytest (« 10 passed, 1 skipped in 0.5s »).

    La dernière ligne utile n'est pas toujours la dernière : pytest termine souvent par la ligne des
    points de progression, on cherche donc la ligne de verdict.
    """
    lignes = [ligne.strip() for ligne in sortie.strip().splitlines() if ligne.strip()]
    for ligne in reversed(lignes):
        if any(mot in ligne for mot in ("passed", "failed", "error", "no tests ran")):
            return ligne[:120]
    return lignes[-1][:120] if lignes else ""


def _etat(s, analyse: Analyse, etat: EtatAnalyse, message: str | None = None) -> None:
    analyse.etat = etat
    if message is not None:
        analyse.message_erreur = message
    s.commit()
    publier_etat_analyse(analyse, message)


def _reinitialiser_alertes(analyse: Analyse) -> None:
    """Vide les alertes d'un essai précédent avant une nouvelle détection.

    Sans cela, une analyse relancée après interruption enregistrerait une seconde fois les mêmes
    alertes : le doublon serait visible dans l'interface et fausserait les compteurs.
    (La cascade `delete-orphan` supprime aussi les tests de preuve et correctifs associés.)
    """
    analyse.failles.clear()
    analyse.message_erreur = None


def preparer_et_detecter(analyse_id: int) -> None:
    """Phase 1 : installe le projet, vérifie les tests existants, lance les scanners (tâche RQ).

    Relançable : une exécution interrompue (conteneur redémarré, tâche abandonnée) peut être
    reprise d'un bout à l'autre sans laisser de doublons.
    """
    with session() as s:
        analyse = s.get(Analyse, analyse_id)
        projet = s.get(Projet, analyse.projet_id)
        racine = Path(projet.chemin_stockage)
        commande_test = projet.commande_test
        _reinitialiser_alertes(analyse)
        _etat(s, analyse, EtatAnalyse.preparation)

    try:
        with BacASable.creer(analyse_id, racine) as bac:
            _information(analyse_id, "Bac à sable créé : installation des dépendances du projet…")
            install = bac.installer()
            if not install.succes:
                return _echec(analyse_id, f"Installation impossible : {install.sortie[-600:]}")
            _information(analyse_id, f"Dépendances installées. {_resume_tests(install.sortie)}".strip())

            existants = bac.executer([*commande_test.split(), "-q", "-p", "no:cacheprovider"])
            if existants.delai_depasse or existants.code_retour != 0:
                return _echec(analyse_id, f"Les tests existants ne passent pas : {existants.sortie[-600:]}")
            _information(analyse_id, f"Tests existants au vert : {_resume_tests(existants.sortie)}")

            with session() as s:
                analyse = s.get(Analyse, analyse_id)
                _etat(s, analyse, EtatAnalyse.detection)
            _information(analyse_id, "Analyse statique en cours : Bandit puis Semgrep, sans réseau.")

            brutes = lancer_scanners(bac)
            alertes = prioriser(fusionner(brutes), racine)
            _enregistrer_alertes(analyse_id, alertes)
            _information(analyse_id,
                         f"{len(brutes)} alertes signalées, {len(alertes)} retenues dans le périmètre "
                         f"des 4 familles.")
    except ErreurBac as e:
        return _echec(analyse_id, str(e))

    with session() as s:
        analyse = s.get(Analyse, analyse_id)
        _etat(s, analyse, EtatAnalyse.selection)


def _enregistrer_alertes(analyse_id: int, alertes) -> None:
    with session() as s:
        for a in alertes:
            s.add(Faille(
                analyse_id=analyse_id, outils=",".join(a.outils), regle=a.regle, fichier=a.fichier,
                ligne=a.ligne, cwe=a.cwe, famille=a.famille or Famille.sqli, gravite=a.gravite,
                exposee=a.exposee, priorite=a.priorite, extrait=a.extrait,
            ))
        s.flush()


def traiter_analyse(analyse_id: int) -> None:
    """Phase 2 : lance les agents sur les failles non exclues (tâche RQ, reprenable)."""
    with session() as s:
        analyse = s.get(Analyse, analyse_id)
        projet = s.get(Projet, analyse.projet_id)
        source = Path(projet.chemin_stockage)
        commande_test = projet.commande_test
        _etat(s, analyse, EtatAnalyse.traitement)
        _information(analyse_id, "Traitement des alertes par les agents (bac à sable reconstruit).")

    # Les agents écrivent dans la copie de travail (tests de preuve, diffs). On travaille sur une
    # copie dédiée à l'analyse pour que le projet importé reste intact et réanalysable à l'identique.
    racine = _copie_de_travail(analyse_id, source)
    try:
        with BacASable.creer(analyse_id, racine) as bac:
            install = bac.installer()
            if not install.succes:
                return _echec(analyse_id, f"Installation impossible : {install.sortie[-600:]}")
            with session() as s:
                analyse = s.get(Analyse, analyse_id)
                traiter_failles(s, analyse, bac, commande_test)
    except AnalyseEnPause as e:
        with session() as s:
            analyse = s.get(Analyse, analyse_id)
            _etat(s, analyse, EtatAnalyse.en_pause, str(e))
        return
    except ErreurBac as e:
        return _echec(analyse_id, str(e))
    finally:
        shutil.rmtree(racine, ignore_errors=True)

    with session() as s:
        analyse = s.get(Analyse, analyse_id)
        analyse.termine_le = maintenant()
        _etat(s, analyse, EtatAnalyse.terminee)


def _copie_de_travail(analyse_id: int, source: Path) -> Path:
    """Copie le projet dans un dossier propre à l'analyse (le projet importé reste intact)."""
    cible = parametres().dossier_donnees / "travail" / str(analyse_id)
    shutil.rmtree(cible, ignore_errors=True)
    shutil.copytree(source, cible, ignore=shutil.ignore_patterns(".git", "__pycache__", ".venv", "node_modules"))
    initialiser_depot(cible)  # l'orchestrateur versionne les correctifs sur cette copie
    return cible


def _echec(analyse_id: int, message: str) -> None:
    with session() as s:
        analyse = s.get(Analyse, analyse_id)
        _etat(s, analyse, EtatAnalyse.echec, message)
    _information(analyse_id, message[:300], succes=False)
    journal.warning("Analyse %s en échec : %s", analyse_id, message)
