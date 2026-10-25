"""Suivi en direct (M6, E-6.1) : chaque étape est enregistrée en base puis diffusée via Redis.

L'API, abonnée au canal Redis de l'analyse, relaie les événements au navigateur par WebSocket.
"""

import json
import logging

from redis import Redis

from patchproof.core.config import parametres
from patchproof.core.db import session
from patchproof.core.modeles import Analyse, EtapeAgent, EtatFaille, Faille
from patchproof.core.schemas import Etape

journal = logging.getLogger("patchproof.suivi")


def canal(analyse_id: int) -> str:
    return f"analyse:{analyse_id}"


def _redis() -> Redis:
    return Redis.from_url(parametres().redis_url)


def _publier_redis(analyse_id: int, message: dict) -> None:
    try:
        _redis().publish(canal(analyse_id), json.dumps(message, ensure_ascii=False))
    except Exception as e:  # noqa: BLE001  la diffusion ne doit jamais interrompre l'analyse
        journal.warning("Diffusion Redis impossible (%s)", e)


def publier_etape(etape: Etape) -> None:
    """Enregistre une étape d'agent et la diffuse (E-6.1, traçabilité 100 %)."""
    with session() as s:
        ligne = EtapeAgent(
            analyse_id=etape.analyse_id, faille_id=etape.faille_id, agent=etape.agent,
            nature=etape.nature, resume=etape.resume, outil=etape.outil, arguments=etape.arguments,
            resultat=etape.resultat, succes=etape.succes,
            jetons_entree=etape.jetons_entree, jetons_sortie=etape.jetons_sortie,
        )
        s.add(ligne)
        s.flush()
        identifiant = ligne.id
        horodatage = ligne.cree_le.isoformat()
    # `resultat` (tronqué) permet au suivi en direct d'afficher le détail d'un outil ou d'un
    # raisonnement sans un aller-retour supplémentaire vers l'API.
    _publier_redis(etape.analyse_id, {
        "type": "etape", "id": identifiant, "faille_id": etape.faille_id, "agent": etape.agent,
        "nature": etape.nature, "resume": etape.resume, "outil": etape.outil, "succes": etape.succes,
        "resultat": (etape.resultat or "")[:1500] or None, "cree_le": horodatage,
    })


def publier_etat_faille(analyse_id: int, faille_id: int, etat: EtatFaille) -> None:
    _publier_redis(analyse_id, {"type": "etat_faille", "faille_id": faille_id, "etat": etat.value})


def publier_etat_analyse(analyse: Analyse, message: str | None = None) -> None:
    _publier_redis(analyse.id, {
        "type": "etat_analyse", "etat": analyse.etat.value, "message": message or analyse.message_erreur,
        "compteurs": compteurs(analyse),
    })


def compteurs(analyse: Analyse) -> dict[str, int]:
    failles = analyse.failles
    par_etat = {e: 0 for e in EtatFaille}
    exclues = 0
    for f in failles:
        par_etat[f.etat] += 1
        exclues += 1 if f.exclue else 0
    return {
        "total": len(failles),
        "exclues": exclues,
        "en_attente": par_etat[EtatFaille.en_attente],
        "confirmees": par_etat[EtatFaille.confirmee],
        "faux_positifs": par_etat[EtatFaille.faux_positif],
        "corrigees": par_etat[EtatFaille.corrigee],
        "revue_humaine": par_etat[EtatFaille.revue_humaine],
    }


def _ignore_faille(f: Faille) -> dict:
    return {"id": f.id, "etat": f.etat}
