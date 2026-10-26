"""Dépendances FastAPI communes : session de base, utilisateur courant, contrôle des rôles."""

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from patchproof.core.db import session_requete
from patchproof.core.erreurs import Interdit, Introuvable, NonAuthentifie
from patchproof.core.modeles import Analyse, Faille, Projet, Role, Utilisateur
from patchproof.core.securite import lire_jeton

SessionBD = Annotated[Session, Depends(session_requete)]

_bearer = HTTPBearer(auto_error=False)

NIVEAUX = {Role.developpeur: 1, Role.responsable_securite: 2, Role.administrateur: 3}


def utilisateur_par_jeton(s: Session, jeton: str) -> Utilisateur:
    utilisateur = s.get(Utilisateur, lire_jeton(jeton))
    if utilisateur is None or not utilisateur.actif:
        raise NonAuthentifie("Compte introuvable ou désactivé")
    return utilisateur


def utilisateur_courant(
    s: SessionBD,
    identifiants: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> Utilisateur:
    if identifiants is None:
        raise NonAuthentifie("Authentification requise")
    return utilisateur_par_jeton(s, identifiants.credentials)


UtilisateurCourant = Annotated[Utilisateur, Depends(utilisateur_courant)]


def exiger_role(role: Role) -> Callable[[Utilisateur], Utilisateur]:
    def verifier(utilisateur: UtilisateurCourant) -> Utilisateur:
        if NIVEAUX[Role(utilisateur.role)] < NIVEAUX[role]:
            raise Interdit("Rôle insuffisant")
        return utilisateur

    return verifier


def peut_tout_voir(utilisateur: Utilisateur) -> bool:
    return NIVEAUX[Role(utilisateur.role)] >= NIVEAUX[Role.responsable_securite]


def projet_accessible(s: Session, projet_id: int, utilisateur: Utilisateur) -> Projet:
    projet = s.get(Projet, projet_id)
    if projet is None:
        raise Introuvable("Projet introuvable")
    if projet.proprietaire_id != utilisateur.id and not peut_tout_voir(utilisateur):
        raise Interdit("Ce projet appartient à un autre utilisateur")
    return projet


def analyse_accessible(s: Session, analyse_id: int, utilisateur: Utilisateur) -> Analyse:
    analyse = s.get(Analyse, analyse_id)
    if analyse is None:
        raise Introuvable("Analyse introuvable")
    projet_accessible(s, analyse.projet_id, utilisateur)
    return analyse


def faille_accessible(s: Session, faille_id: int, utilisateur: Utilisateur) -> Faille:
    faille = s.get(Faille, faille_id)
    if faille is None:
        raise Introuvable("Faille introuvable")
    analyse_accessible(s, faille.analyse_id, utilisateur)
    return faille
