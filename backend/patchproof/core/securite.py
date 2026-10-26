"""Mots de passe (bcrypt), jetons de session (JWT) et chiffrement des jetons GitHub (Fernet)."""

from datetime import UTC, datetime, timedelta

import bcrypt
import jwt
from cryptography.fernet import Fernet, InvalidToken

from patchproof.core.config import parametres
from patchproof.core.erreurs import ErreurApi, NonAuthentifie


def hacher_mot_de_passe(mot_de_passe: str) -> str:
    return bcrypt.hashpw(mot_de_passe.encode(), bcrypt.gensalt()).decode()


def verifier_mot_de_passe(mot_de_passe: str, hachage: str) -> bool:
    return bcrypt.checkpw(mot_de_passe.encode(), hachage.encode())


def creer_jeton(utilisateur_id: int) -> str:
    p = parametres()
    charge = {
        "sub": str(utilisateur_id),
        "exp": datetime.now(UTC) + timedelta(hours=p.jwt_duree_heures),
    }
    return jwt.encode(charge, p.jwt_secret, algorithm="HS256")


def lire_jeton(jeton: str) -> int:
    try:
        charge = jwt.decode(jeton, parametres().jwt_secret, algorithms=["HS256"])
        return int(charge["sub"])
    except (jwt.PyJWTError, KeyError, ValueError) as e:
        raise NonAuthentifie("Session invalide ou expirée") from e


def _fernet() -> Fernet:
    cle = parametres().cle_chiffrement
    if not cle:
        raise ErreurApi("CLE_CHIFFREMENT n'est pas configurée", code="configuration", statut=500)
    return Fernet(cle.encode())


def chiffrer(texte: str) -> str:
    return _fernet().encrypt(texte.encode()).decode()


def dechiffrer(texte: str) -> str:
    try:
        return _fernet().decrypt(texte.encode()).decode()
    except InvalidToken as e:
        raise ErreurApi("Jeton GitHub illisible, reconnectez GitHub", code="github_jeton") from e
