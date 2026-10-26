"""Routes du rapport : JSON, détail d'une faille, export PDF (docs/api.md)."""

from fastapi import APIRouter
from fastapi.responses import Response

from patchproof.api.deps import SessionBD, UtilisateurCourant, analyse_accessible, faille_accessible
from patchproof.rapport.rapport import construire_rapport, exporter_pdf

router = APIRouter(tags=["rapport"])


@router.get("/api/analyses/{analyse_id}/rapport")
def rapport_json(analyse_id: int, s: SessionBD, utilisateur: UtilisateurCourant) -> dict:
    analyse = analyse_accessible(s, analyse_id, utilisateur)
    return construire_rapport(s, analyse)


@router.get("/api/analyses/{analyse_id}/rapport.pdf")
def rapport_pdf(analyse_id: int, s: SessionBD, utilisateur: UtilisateurCourant) -> Response:
    analyse = analyse_accessible(s, analyse_id, utilisateur)
    pdf = exporter_pdf(construire_rapport(s, analyse))
    return Response(
        content=pdf, media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="rapport-patchproof-{analyse_id}.pdf"'},
    )


@router.get("/api/failles/{faille_id}/detail")
def detail_faille(faille_id: int, s: SessionBD, utilisateur: UtilisateurCourant) -> dict:
    faille = faille_accessible(s, faille_id, utilisateur)
    return {
        "id": faille.id, "fichier": faille.fichier, "ligne": faille.ligne, "cwe": faille.cwe,
        "famille": faille.famille.value, "gravite": faille.gravite, "etat": faille.etat.value,
        "point_entree": faille.point_entree, "justification": faille.justification,
        "extrait": faille.extrait,
        "test_preuve": (
            {"chemin": faille.test_preuve.chemin, "contenu": faille.test_preuve.contenu}
            if faille.test_preuve else None
        ),
        "correctifs": [
            {"id": c.id, "tentative": c.tentative, "diff": c.diff, "explication": c.explication,
             "valide": c.valide, "decision": c.decision, "resultat_validation": c.resultat_validation}
            for c in sorted(faille.correctifs, key=lambda c: c.tentative)
        ],
    }
