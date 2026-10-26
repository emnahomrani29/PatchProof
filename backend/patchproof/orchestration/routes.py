"""Routes des analyses : création, sélection des alertes, lancement, reprise (docs/api.md)."""

from fastapi import APIRouter
from redis import Redis
from rq import Queue
from sqlalchemy import select

from patchproof.api.deps import (
    SessionBD,
    UtilisateurCourant,
    analyse_accessible,
    faille_accessible,
    projet_accessible,
)
from patchproof.core.config import parametres
from patchproof.core.erreurs import Invalide
from patchproof.core.modeles import Analyse, EtatAnalyse, Faille, ParametresAdmin
from patchproof.core.schemas import AnalyseSortie, Compteurs, FailleSortie, ModifFaille
from patchproof.suivi.publication import compteurs

router = APIRouter(tags=["analyses"])


def file() -> Queue:
    return Queue("analyses", connection=Redis.from_url(parametres().redis_url))


def _vers_sortie(analyse: Analyse) -> AnalyseSortie:
    sortie = AnalyseSortie.model_validate(analyse)
    sortie.compteurs = Compteurs(**compteurs(analyse))
    return sortie


@router.post("/api/projets/{projet_id}/analyses", response_model=AnalyseSortie, status_code=202)
def creer_analyse(projet_id: int, s: SessionBD, utilisateur: UtilisateurCourant) -> AnalyseSortie:
    projet = projet_accessible(s, projet_id, utilisateur)
    params = s.get(ParametresAdmin, 1)
    analyse = Analyse(projet_id=projet.id, etat=EtatAnalyse.en_attente, parametres={
        "budget_jetons_analyse": params.budget_jetons_analyse,
        "max_tentatives_agent": params.max_tentatives_agent,
        "max_appels_outils_faille": params.max_appels_outils_faille,
    })
    s.add(analyse)
    s.flush()
    s.commit()
    file().enqueue("patchproof.orchestration.analyse.preparer_et_detecter", analyse.id, job_timeout=1800)
    return _vers_sortie(analyse)


@router.get("/api/projets/{projet_id}/analyses", response_model=list[AnalyseSortie])
def historique(projet_id: int, s: SessionBD, utilisateur: UtilisateurCourant) -> list[AnalyseSortie]:
    projet_accessible(s, projet_id, utilisateur)
    analyses = s.scalars(select(Analyse).where(Analyse.projet_id == projet_id).order_by(Analyse.id.desc()))
    return [_vers_sortie(a) for a in analyses]


@router.get("/api/analyses/{analyse_id}", response_model=AnalyseSortie)
def lire_analyse(analyse_id: int, s: SessionBD, utilisateur: UtilisateurCourant) -> AnalyseSortie:
    return _vers_sortie(analyse_accessible(s, analyse_id, utilisateur))


@router.get("/api/analyses/{analyse_id}/failles", response_model=list[FailleSortie])
def lister_failles(analyse_id: int, s: SessionBD, utilisateur: UtilisateurCourant) -> list[Faille]:
    analyse = analyse_accessible(s, analyse_id, utilisateur)
    return sorted(analyse.failles, key=lambda f: f.priorite)


@router.patch("/api/failles/{faille_id}", response_model=FailleSortie)
def exclure_faille(faille_id: int, corps: ModifFaille, s: SessionBD, utilisateur: UtilisateurCourant) -> Faille:
    faille = faille_accessible(s, faille_id, utilisateur)
    if faille.analyse.etat != EtatAnalyse.selection:
        raise Invalide("Les alertes ne peuvent être exclues qu'avant le lancement des agents.")
    faille.exclue = corps.exclue
    return faille


@router.post("/api/analyses/{analyse_id}/demarrer", response_model=AnalyseSortie, status_code=202)
def demarrer(analyse_id: int, s: SessionBD, utilisateur: UtilisateurCourant) -> AnalyseSortie:
    analyse = analyse_accessible(s, analyse_id, utilisateur)
    if analyse.etat != EtatAnalyse.selection:
        raise Invalide("L'analyse n'est pas à l'étape de sélection des alertes.")
    analyse.etat = EtatAnalyse.traitement
    s.commit()
    file().enqueue("patchproof.orchestration.analyse.traiter_analyse", analyse.id, job_timeout=3600)
    return _vers_sortie(analyse)


@router.post("/api/analyses/{analyse_id}/reprendre", response_model=AnalyseSortie, status_code=202)
def reprendre(analyse_id: int, s: SessionBD, utilisateur: UtilisateurCourant) -> AnalyseSortie:
    analyse = analyse_accessible(s, analyse_id, utilisateur)
    if analyse.etat != EtatAnalyse.en_pause:
        raise Invalide("Seule une analyse en pause peut être reprise.")
    analyse.etat = EtatAnalyse.traitement
    analyse.message_erreur = None
    s.commit()
    file().enqueue("patchproof.orchestration.analyse.traiter_analyse", analyse.id, job_timeout=3600)
    return _vers_sortie(analyse)


# États depuis lesquels une relance a un sens, et tâche à relancer.
TACHES_RELANCE = {
    EtatAnalyse.en_attente: ("patchproof.orchestration.analyse.preparer_et_detecter", 1800),
    EtatAnalyse.preparation: ("patchproof.orchestration.analyse.preparer_et_detecter", 1800),
    EtatAnalyse.detection: ("patchproof.orchestration.analyse.preparer_et_detecter", 1800),
    EtatAnalyse.echec: ("patchproof.orchestration.analyse.preparer_et_detecter", 1800),
    EtatAnalyse.traitement: ("patchproof.orchestration.analyse.traiter_analyse", 3600),
    EtatAnalyse.en_pause: ("patchproof.orchestration.analyse.traiter_analyse", 3600),
}


@router.post("/api/analyses/{analyse_id}/relancer", response_model=AnalyseSortie, status_code=202)
def relancer(analyse_id: int, s: SessionBD, utilisateur: UtilisateurCourant) -> AnalyseSortie:
    """Relance une analyse interrompue, dans la phase où elle s'est arrêtée.

    Une analyse dont la tâche a été abandonnée (conteneur redémarré pendant l'analyse, coupure)
    reste sinon bloquée dans son dernier état, et l'interface attend indéfiniment. La phase de
    préparation repart d'une liste d'alertes propre, et le traitement ignore les failles déjà
    terminées : relancer ne refait pas le travail déjà fait.
    """
    analyse = analyse_accessible(s, analyse_id, utilisateur)
    tache = TACHES_RELANCE.get(analyse.etat)
    if tache is None:
        if analyse.etat == EtatAnalyse.selection:
            raise Invalide("L'analyse attend la sélection des alertes : utilisez « Lancer les agents ».")
        raise Invalide("Cette analyse est terminée, elle n'a pas besoin d'être relancée.")
    fonction, delai = tache
    analyse.message_erreur = None
    s.commit()
    file().enqueue(fonction, analyse.id, job_timeout=delai)
    return _vers_sortie(analyse)
