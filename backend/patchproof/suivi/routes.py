"""Routes du suivi : historique des étapes et flux WebSocket en direct (docs/api.md)."""

import asyncio
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from redis import Redis
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
    # Authentification via le paramètre de requête (les WebSocket ne portent pas d'en-tête Bearer).
    try:
        with session() as s:
            utilisateur = utilisateur_par_jeton(s, jeton)
            analyse = analyse_accessible(s, analyse_id, utilisateur)
            etat_initial = {"type": "etat_analyse", "etat": analyse.etat.value,
                            "message": analyse.message_erreur, "compteurs": compteurs(analyse)}
    except Exception:  # noqa: BLE001  jeton invalide ou analyse inaccessible : on refuse la connexion
        # Sans cette trace, un refus avant `accept()` n'apparaît que comme un 403 sans explication.
        journal.warning("Suivi refusé pour l'analyse %s", analyse_id, exc_info=True)
        await websocket.close(code=4401)
        return

    await websocket.accept()
    await websocket.send_json(etat_initial)

    pubsub = Redis.from_url(parametres().redis_url).pubsub()
    pubsub.subscribe(canal(analyse_id))
    try:
        while True:
            message = pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if message and message.get("type") == "message":
                donnees = message["data"]
                await websocket.send_text(donnees.decode() if isinstance(donnees, bytes) else donnees)
            await asyncio.sleep(0.05)  # laisse la main à la boucle asyncio
    except WebSocketDisconnect:
        pass
    finally:
        pubsub.close()
