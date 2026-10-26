"""Construction du rapport d'analyse et export PDF (M6, E-6.2)."""

import html

from sqlalchemy.orm import Session

from patchproof.core.modeles import Analyse, EtatFaille
from patchproof.suivi.publication import compteurs

LIBELLE_ETAT = {
    EtatFaille.corrigee: "Corrigée", EtatFaille.faux_positif: "Faux positif",
    EtatFaille.revue_humaine: "Revue humaine", EtatFaille.confirmee: "Confirmée",
    EtatFaille.en_cours: "En cours", EtatFaille.en_attente: "En attente",
}


def construire_rapport(s: Session, analyse: Analyse) -> dict:
    failles = sorted(analyse.failles, key=lambda f: f.priorite)
    return {
        "analyse_id": analyse.id,
        "projet": analyse.projet.nom,
        "etat": analyse.etat.value,
        "compteurs": compteurs(analyse),
        "cout_estime_usd": round(analyse.cout_estime_usd, 4),
        "jetons_utilises": analyse.jetons_utilises,
        "failles": [
            {
                "id": f.id, "fichier": f.fichier, "ligne": f.ligne, "cwe": f.cwe,
                "famille": f.famille.value, "gravite": f.gravite, "etat": f.etat.value,
                "etat_libelle": LIBELLE_ETAT.get(f.etat, f.etat.value),
                "justification": f.justification,
                "test_preuve": f.test_preuve.contenu if f.test_preuve else None,
                "correctif": _dernier_correctif(f),
            }
            for f in failles if not f.exclue
        ],
    }


def _dernier_correctif(faille) -> dict | None:
    accepte = next((c for c in faille.correctifs if c.decision != "rejete" and c.valide), None)
    dernier = accepte or (faille.correctifs[-1] if faille.correctifs else None)
    if dernier is None:
        return None
    return {"diff": dernier.diff, "explication": dernier.explication, "valide": dernier.valide}


def exporter_pdf(rapport: dict) -> bytes:
    """Rend le rapport en PDF via WeasyPrint (métadonnées réduites au seul titre)."""
    from weasyprint import HTML  # import tardif : dépendance lourde

    document = HTML(string=_html(rapport)).render()
    document.metadata.title = f"Rapport PatchProof — {rapport['projet']}"
    document.metadata.authors = []
    document.metadata.generator = ""
    return document.write_pdf()


def _html(r: dict) -> str:
    c = r["compteurs"]
    lignes = "".join(
        f"<section class='faille {f['etat']}'>"
        f"<h3>{html.escape(f['fichier'])}:{f['ligne']} — {html.escape(f['famille'])} "
        f"<span class='badge'>{html.escape(f['etat_libelle'])}</span></h3>"
        f"<p class='cwe'>{html.escape(f['cwe'])}</p>"
        + (f"<p>{html.escape(f['justification'])}</p>" if f["justification"] else "")
        + (f"<h4>Test de preuve</h4><pre>{html.escape(f['test_preuve'])}</pre>" if f["test_preuve"] else "")
        + (f"<h4>Correctif</h4><pre>{html.escape(f['correctif']['diff'])}</pre>"
           if f["correctif"] else "")
        + "</section>"
        for f in r["failles"]
    )
    return f"""<!doctype html><html lang="fr"><head><meta charset="utf-8">
<title>Rapport PatchProof — {html.escape(r['projet'])}</title>
<style>
  @page {{ margin: 2cm; }}
  body {{ font-family: sans-serif; color: #1c2330; font-size: 12px; }}
  h1 {{ color: #531729; }}
  .resume {{ display: flex; gap: 14px; margin: 16px 0; flex-wrap: wrap; }}
  .resume div {{ border: 1px solid #ddd; border-radius: 8px; padding: 10px 14px; }}
  .resume b {{ font-size: 22px; display: block; }}
  .faille {{ border: 1px solid #e0d6d2; border-radius: 8px; padding: 10px 14px; margin: 10px 0; }}
  .badge {{ font-size: 10px; padding: 2px 8px; border-radius: 10px; background: #eee; }}
  .corrigee .badge {{ background: #e3f4ea; color: #1f8a4c; }}
  .faux_positif .badge {{ background: #eceef2; }}
  .revue_humaine .badge {{ background: #fbe7e5; color: #c4372b; }}
  pre {{ background: #f6f4f0; padding: 8px; border-radius: 6px; white-space: pre-wrap; font-size: 10px; }}
  .cwe {{ color: #777; font-size: 10px; }}
</style></head><body>
<h1>Rapport PatchProof — {html.escape(r['projet'])}</h1>
<div class="resume">
  <div><b>{c['total']}</b>alertes</div>
  <div><b>{c['corrigees']}</b>corrigées</div>
  <div><b>{c['faux_positifs']}</b>faux positifs</div>
  <div><b>{c['revue_humaine']}</b>revue humaine</div>
  <div><b>{r['cout_estime_usd']} $</b>coût</div>
</div>
{lignes}
</body></html>"""
