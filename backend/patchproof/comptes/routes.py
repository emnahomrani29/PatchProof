"""Routes du module 1 : authentification, projets, administration (docs/api.md)."""

import secrets
import shutil
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, File, Response, UploadFile
from fastapi.responses import RedirectResponse
from sqlalchemy import func, select

from patchproof.api.deps import (
    SessionBD,
    UtilisateurCourant,
    exiger_role,
    peut_tout_voir,
    projet_accessible,
    utilisateur_par_jeton,
)
from patchproof.comptes.projets import cloner_github, detecter_framework, dossier_projet, extraire_zip
from patchproof.core.config import parametres
from patchproof.core.erreurs import Conflit, ErreurApi, Introuvable, Invalide, NonAuthentifie
from patchproof.core.modeles import ParametresAdmin, Projet, Role, Utilisateur
from patchproof.core.schemas import (
    Connexion,
    Inscription,
    JetonSortie,
    ModifUtilisateur,
    NouveauProjetGithub,
    ParametresSortie,
    ProjetSortie,
    UtilisateurSortie,
)
from patchproof.core.securite import chiffrer, creer_jeton, hacher_mot_de_passe, verifier_mot_de_passe

router = APIRouter(tags=["comptes"])

# --- Authentification ---------------------------------------------------------------


@router.post("/api/auth/inscription", response_model=UtilisateurSortie, status_code=201)
def inscription(corps: Inscription, s: SessionBD) -> Utilisateur:
    if s.scalar(select(Utilisateur).where(Utilisateur.email == corps.email.lower())):
        raise Conflit("Un compte existe déjà avec cet e-mail.")
    premier = (s.scalar(select(func.count(Utilisateur.id))) or 0) == 0
    utilisateur = Utilisateur(
        email=corps.email.lower(),
        nom=corps.nom,
        mot_de_passe_hash=hacher_mot_de_passe(corps.mot_de_passe),
        # Le tout premier compte administre la plateforme.
        role=Role.administrateur if premier else Role.developpeur,
    )
    s.add(utilisateur)
    s.flush()
    return utilisateur


@router.post("/api/auth/connexion", response_model=JetonSortie)
def connexion(corps: Connexion, s: SessionBD) -> JetonSortie:
    utilisateur = s.scalar(select(Utilisateur).where(Utilisateur.email == corps.email.lower()))
    if not utilisateur or not verifier_mot_de_passe(corps.mot_de_passe, utilisateur.mot_de_passe_hash):
        raise NonAuthentifie("E-mail ou mot de passe incorrect.")
    if not utilisateur.actif:
        raise NonAuthentifie("Compte désactivé.")
    return JetonSortie(jeton=creer_jeton(utilisateur.id), utilisateur=UtilisateurSortie.model_validate(utilisateur))


@router.post("/api/auth/deconnexion", status_code=204)
def deconnexion() -> Response:
    return Response(status_code=204)


@router.get("/api/auth/moi", response_model=UtilisateurSortie)
def moi(utilisateur: UtilisateurCourant) -> Utilisateur:
    return utilisateur


# --- GitHub OAuth ---------------------------------------------------------------------

_etats_oauth: dict[str, int] = {}


@router.get("/api/auth/github")
def github_autorisation(utilisateur: UtilisateurCourant) -> dict[str, str]:
    p = parametres()
    if not p.github_client_id:
        raise ErreurApi("GitHub OAuth n'est pas configuré (GITHUB_CLIENT_ID).", code="github_non_configure", statut=503)
    etat = secrets.token_urlsafe(24)
    _etats_oauth[etat] = utilisateur.id
    requete = urlencode({
        "client_id": p.github_client_id,
        "redirect_uri": f"{p.url_api}/api/auth/github/retour",
        "scope": "public_repo",
        "state": etat,
    })
    return {"url": f"https://github.com/login/oauth/authorize?{requete}"}


@router.get("/api/auth/github/retour")
def github_retour(code: str, state: str, s: SessionBD) -> RedirectResponse:
    p = parametres()
    utilisateur_id = _etats_oauth.pop(state, None)
    if utilisateur_id is None:
        raise Invalide("État OAuth inconnu ou expiré.")
    reponse = httpx.post(
        "https://github.com/login/oauth/access_token",
        data={"client_id": p.github_client_id, "client_secret": p.github_client_secret, "code": code},
        headers={"Accept": "application/json"},
        timeout=20,
    ).json()
    jeton = reponse.get("access_token")
    if not jeton:
        raise Invalide("GitHub a refusé l'autorisation.")
    profil = httpx.get("https://api.github.com/user", headers={"Authorization": f"Bearer {jeton}"}, timeout=20).json()
    utilisateur = s.get(Utilisateur, utilisateur_id)
    utilisateur.github_jeton_chiffre = chiffrer(jeton)
    utilisateur.github_login = profil.get("login")
    return RedirectResponse(f"{p.url_frontend}/projets?github=ok")


# --- Projets ---------------------------------------------------------------------------


def _finaliser(s, projet: Projet, sha: str) -> Projet:
    racine = dossier_projet(projet.id)
    info = detecter_framework(racine)
    if info.nb_lignes > parametres().max_lignes_projet:
        shutil.rmtree(racine, ignore_errors=True)
        raise Invalide(f"Projet trop gros : {info.nb_lignes} lignes Python (5 000 au plus).", code="projet_trop_gros")
    if info.framework is None:
        shutil.rmtree(racine, ignore_errors=True)
        raise Invalide("Ni Flask ni FastAPI n'a été détecté dans ce projet.", code="framework_non_supporte")
    projet.chemin_stockage = str(racine)
    projet.commit_sha = sha
    projet.framework = info.framework
    projet.commande_test = info.commande_test
    projet.nb_lignes = info.nb_lignes
    return projet


@router.get("/api/projets", response_model=list[ProjetSortie])
def lister_projets(s: SessionBD, utilisateur: UtilisateurCourant) -> list[Projet]:
    requete = select(Projet).order_by(Projet.id.desc())
    if not peut_tout_voir(utilisateur):
        requete = requete.where(Projet.proprietaire_id == utilisateur.id)
    return list(s.scalars(requete))


@router.post("/api/projets", response_model=ProjetSortie, status_code=201)
def importer_github(corps: NouveauProjetGithub, s: SessionBD, utilisateur: UtilisateurCourant) -> Projet:
    url = corps.url_github.rstrip("/")
    projet = Projet(proprietaire_id=utilisateur.id, nom=url.split("/")[-1], source="github",
                    url_github=url, chemin_stockage="")
    s.add(projet)
    s.flush()
    sha = cloner_github(url, dossier_projet(projet.id))
    return _finaliser(s, projet, sha)


@router.post("/api/projets/zip", response_model=ProjetSortie, status_code=201)
async def importer_zip(
    s: SessionBD, utilisateur: UtilisateurCourant, fichier: UploadFile = File(...)  # noqa: B008
) -> Projet:
    contenu = await fichier.read()
    nom = (fichier.filename or "projet.zip").rsplit(".", 1)[0][:200]
    projet = Projet(proprietaire_id=utilisateur.id, nom=nom, source="zip", chemin_stockage="")
    s.add(projet)
    s.flush()
    sha = extraire_zip(contenu, dossier_projet(projet.id))
    return _finaliser(s, projet, sha)


@router.get("/api/projets/{projet_id}", response_model=ProjetSortie)
def lire_projet(projet_id: int, s: SessionBD, utilisateur: UtilisateurCourant) -> Projet:
    return projet_accessible(s, projet_id, utilisateur)


@router.delete("/api/projets/{projet_id}", status_code=204)
def supprimer_projet(projet_id: int, s: SessionBD, utilisateur: UtilisateurCourant) -> Response:
    projet = projet_accessible(s, projet_id, utilisateur)
    shutil.rmtree(dossier_projet(projet.id), ignore_errors=True)
    s.delete(projet)
    return Response(status_code=204)


# --- Administration ----------------------------------------------------------------------

admin = Depends(exiger_role(Role.administrateur))


@router.get("/api/admin/utilisateurs", response_model=list[UtilisateurSortie], dependencies=[admin])
def lister_utilisateurs(s: SessionBD) -> list[Utilisateur]:
    return list(s.scalars(select(Utilisateur).order_by(Utilisateur.id)))


@router.patch("/api/admin/utilisateurs/{utilisateur_id}", response_model=UtilisateurSortie, dependencies=[admin])
def modifier_utilisateur(utilisateur_id: int, corps: ModifUtilisateur, s: SessionBD) -> Utilisateur:
    cible = s.get(Utilisateur, utilisateur_id)
    if cible is None:
        raise Introuvable("Utilisateur introuvable.")
    if corps.role is not None:
        cible.role = corps.role
    if corps.actif is not None:
        cible.actif = corps.actif
    return cible


@router.get("/api/admin/parametres", response_model=ParametresSortie, dependencies=[admin])
def lire_parametres(s: SessionBD) -> ParametresAdmin:
    return s.get(ParametresAdmin, 1)


@router.put("/api/admin/parametres", response_model=ParametresSortie, dependencies=[admin])
def modifier_parametres(corps: ParametresSortie, s: SessionBD) -> ParametresAdmin:
    ligne = s.get(ParametresAdmin, 1)
    for champ, valeur in corps.model_dump().items():
        setattr(ligne, champ, valeur)
    return ligne


__all__ = ["router", "utilisateur_par_jeton"]
