"""Cycle de vie d'une analyse (tâche RQ exécutée par le worker).

preparation -> detection -> selection (attente du développeur) -> traitement -> terminee,
avec en_pause (quota/budget) et echec (installation ou tests existants KO). Reprenable.
"""

import logging
from pathlib import Path

from patchproof.core.db import session
from patchproof.core.modeles import Analyse, EtatAnalyse, Faille, Famille, Projet, maintenant
from patchproof.detection.priorisation import fusionner, prioriser
from patchproof.detection.scanners import lancer_scanners
from patchproof.orchestration.orchestrateur import AnalyseEnPause, traiter_failles
from patchproof.sandbox.bac import BacASable, ErreurBac
from patchproof.suivi.publication import publier_etat_analyse

journal = logging.getLogger("patchproof.analyse")


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
            install = bac.installer()
            if not install.succes:
                return _echec(analyse_id, f"Installation impossible : {install.sortie[-600:]}")

            existants = bac.executer([*commande_test.split(), "-q", "-p", "no:cacheprovider"])
            if existants.delai_depasse or existants.code_retour != 0:
                return _echec(analyse_id, f"Les tests existants ne passent pas : {existants.sortie[-600:]}")

            with session() as s:
                analyse = s.get(Analyse, analyse_id)
                _etat(s, analyse, EtatAnalyse.detection)

            alertes = prioriser(fusionner(lancer_scanners(bac)), racine)
            _enregistrer_alertes(analyse_id, alertes)
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
        racine = Path(projet.chemin_stockage)
        commande_test = projet.commande_test
        _etat(s, analyse, EtatAnalyse.traitement)

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

    with session() as s:
        analyse = s.get(Analyse, analyse_id)
        analyse.termine_le = maintenant()
        _etat(s, analyse, EtatAnalyse.terminee)


def _echec(analyse_id: int, message: str) -> None:
    with session() as s:
        analyse = s.get(Analyse, analyse_id)
        _etat(s, analyse, EtatAnalyse.echec, message)
    journal.warning("Analyse %s en échec : %s", analyse_id, message)
