"""Application FastAPI : assemble les routes fournies par chaque module.

Un module dont les routes ne sont pas encore écrites est simplement ignoré,
ce qui permet d'intégrer les modules un par un.
"""

import importlib
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from patchproof.core.config import parametres
from patchproof.core.db import creer_tables, session
from patchproof.core.erreurs import ErreurApi
from patchproof.core.modeles import ParametresAdmin

MODULES_AVEC_ROUTES = ["comptes", "orchestration", "suivi", "rapport", "livraison"]

journal = logging.getLogger("patchproof")


def initialiser_parametres() -> None:
    p = parametres()
    with session() as s:
        if s.get(ParametresAdmin, 1) is None:
            s.add(ParametresAdmin(
                id=1,
                budget_jetons_analyse=p.budget_jetons_analyse,
                max_tentatives_agent=p.max_tentatives_agent,
                max_appels_outils_faille=p.max_appels_outils_faille,
                modele_attaquant=p.modele_attaquant,
                modele_defenseur=p.modele_defenseur,
                modele_leger=p.modele_leger,
            ))


@asynccontextmanager
async def cycle_de_vie(_app: FastAPI):
    creer_tables()
    initialiser_parametres()
    parametres().dossier_projets.mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(title="PatchProof", version="0.1.0", lifespan=cycle_de_vie)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[parametres().url_frontend],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(ErreurApi)
async def gerer_erreur_api(_requete: Request, erreur: ErreurApi) -> JSONResponse:
    return JSONResponse(status_code=erreur.statut, content={"detail": erreur.detail, "code": erreur.code})


@app.get("/api/sante", tags=["socle"])
def sante() -> dict[str, object]:
    return {"etat": "ok", "modules": modules_charges}


modules_charges: list[str] = []
for nom in MODULES_AVEC_ROUTES:
    try:
        module = importlib.import_module(f"patchproof.{nom}.routes")
    except ModuleNotFoundError as e:
        if e.name != f"patchproof.{nom}.routes":
            raise
        journal.warning("Routes du module %s absentes : ignorées", nom)
        continue
    app.include_router(module.router)
    modules_charges.append(nom)
