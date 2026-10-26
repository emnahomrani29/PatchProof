"""Routes de livraison : décision sur un correctif, patch, pull request, revue humaine."""

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy import select

from patchproof.api.deps import (
    SessionBD,
    UtilisateurCourant,
    analyse_accessible,
    exiger_role,
    faille_accessible,
)
from patchproof.core.erreurs import ErreurApi, Introuvable, Invalide
from patchproof.core.modeles import Correctif, EtatFaille, Faille, Role, Utilisateur
from patchproof.core.schemas import DecisionCorrectif, DecisionRevue, DemandePullRequest, FailleSortie
from patchproof.core.securite import dechiffrer
from patchproof.livraison.livraison import generer_patch, ouvrir_pull_request

router = APIRouter(tags=["livraison"])


@router.patch("/api/correctifs/{correctif_id}")
def decider_correctif(correctif_id: int, corps: DecisionCorrectif, s: SessionBD,
                      utilisateur: UtilisateurCourant) -> dict:
    correctif = s.get(Correctif, correctif_id)
    if correctif is None:
        raise Introuvable("Correctif introuvable.")
    faille_accessible(s, correctif.faille_id, utilisateur)
    correctif.decision = corps.decision
    return {"id": correctif.id, "decision": correctif.decision}


@router.get("/api/analyses/{analyse_id}/patch")
def patch(analyse_id: int, s: SessionBD, utilisateur: UtilisateurCourant) -> Response:
    analyse = analyse_accessible(s, analyse_id, utilisateur)
    return Response(
        content=generer_patch(analyse), media_type="text/x-diff",
        headers={"Content-Disposition": f'attachment; filename="patchproof-{analyse_id}.patch"'},
    )


@router.post("/api/analyses/{analyse_id}/pull-request")
def pull_request(analyse_id: int, corps: DemandePullRequest, s: SessionBD,
                 utilisateur: UtilisateurCourant) -> dict:
    analyse = analyse_accessible(s, analyse_id, utilisateur)
    proprietaire = s.get(Utilisateur, analyse.projet.proprietaire_id)
    if not proprietaire.github_jeton_chiffre:
        raise ErreurApi("Connectez un compte GitHub pour ouvrir une pull request.",
                        code="github_non_connecte", statut=400)
    try:
        url = ouvrir_pull_request(s, analyse, dechiffrer(proprietaire.github_jeton_chiffre),
                                  corps.branche, corps.titre)
    except ValueError as e:
        raise Invalide(str(e), code="pull_request") from e
    return {"url": url}


# --- Revue humaine (responsable sécurité) ---

revue = Depends(exiger_role(Role.responsable_securite))


@router.get("/api/revue", response_model=list[FailleSortie], dependencies=[revue])
def failles_en_revue(s: SessionBD) -> list[Faille]:
    return list(s.scalars(select(Faille).where(Faille.etat == EtatFaille.revue_humaine).order_by(Faille.id)))


@router.post("/api/failles/{faille_id}/revue", response_model=FailleSortie, dependencies=[revue])
def traiter_revue(faille_id: int, corps: DecisionRevue, s: SessionBD) -> Faille:
    faille = s.get(Faille, faille_id)
    if faille is None:
        raise Introuvable("Faille introuvable.")
    if faille.etat != EtatFaille.revue_humaine:
        raise Invalide("Cette faille n'est pas en revue humaine.")
    faille.decision_revue = corps.decision
    faille.commentaire_revue = corps.commentaire
    if corps.decision == "faux_positif":
        faille.etat = EtatFaille.faux_positif
    elif corps.decision == "corrigee_manuellement":
        faille.etat = EtatFaille.corrigee
    return faille
