"""Routes du suivi : historique des étapes et flux WebSocket en direct (docs/api.md)."""

import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from redis.asyncio import Redis as RedisAsync
from sqlalchemy import select

from patchproof.api.deps import SessionBD, UtilisateurCourant, analyse_accessible, utilisateur_par_jeton
from patchproof.core.config import parametres
from patchproof.core.db import session
from patchproof.core.modeles import EtapeAgent
from patchproof.core.schemas import EtapeSortie
from patchproof.suivi.publication import canal, compteurs

journal = logging.getLogger("patchproof.suivi")
router = APIRouter(tags=["suivi"])


@router.get("/api/analyses/{analyse_id}/etapes", response_model=list[EtapeSortie])
def etapes(analyse_id: int, s: SessionBD, utilisateur: UtilisateurCourant,
           faille_id: int | None = None) -> list[EtapeAgent]:
    analyse_accessible(s, analyse_id, utilisateur)
    requete = select(EtapeAgent).where(EtapeAgent.analyse_id == analyse_id).order_by(EtapeAgent.id)
    if faille_id is not None:
        requete = requete.where(EtapeAgent.faille_id == faille_id)
    return list(s.scalars(requete))


@router.websocket("/ws/analyses/{analyse_id}")
async def suivi_direct(websocket: WebSocket, analyse_id: int, jeton: str = "") -> None:
    # On accepte toujours la connexion d'abord : un refus avant accept() est renvoyé par Starlette
    # comme un simple 403 de handshake (code de fermeture 1006 côté client), que le client ne peut
    # pas distinguer d'une coupure réseau et qu'il réessaie en boucle. En acceptant puis en fermant
    # avec un code applicatif (4401), le client sait que c'est une authentification refusée.
    await websocket.accept()

    # Authentification via le paramètre de requête (les WebSocket ne portent pas d'en-tête Bearer).
    try:
        with session() as s:
            utilisateur = utilisateur_par_jeton(s, jeton)
            analyse = analyse_accessible(s, analyse_id, utilisateur)
            etat_initial = {"type": "etat_analyse", "etat": analyse.etat.value,
                            "message": analyse.message_erreur, "compteurs": compteurs(analyse)}
    except Exception:  # noqa: BLE001  jeton invalide ou analyse inaccessible : on refuse la connexion
        journal.warning("Suivi refusé pour l'analyse %s", analyse_id, exc_info=True)
        await websocket.close(code=4401)
        return

    await websocket.send_json(etat_initial)

    # Client Redis asynchrone : `get_message` ne bloque PAS la boucle d'événements uvicorn.
    # Avec le client synchrone, chaque attente de message figeait le serveur entier (jusqu'à 1 s par
    # tour), ce qui ralentissait toutes les requêtes HTTP tant qu'un suivi était ouvert.
    redis = RedisAsync.from_url(parametres().redis_url)
    pubsub = redis.pubsub()
    await pubsub.subscribe(canal(analyse_id))
    try:
        async for message in pubsub.listen():
            if message.get("type") == "message":
                donnees = message["data"]
                await websocket.send_text(donnees.decode() if isinstance(donnees, bytes) else donnees)
    except (WebSocketDisconnect, RuntimeError):
        # Déconnexion du client : détectée à l'envoi suivant (RuntimeError de Starlette) ou
        # directement (WebSocketDisconnect). Dans les deux cas, on nettoie l'abonnement Redis.
        pass
    finally:
        await pubsub.aclose()
        await redis.aclose()
