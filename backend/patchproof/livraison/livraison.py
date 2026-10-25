"""Génération du patch et ouverture d'une pull request GitHub (M6, E-6.3)."""

import base64
import logging

import httpx
from sqlalchemy.orm import Session

from patchproof.core.modeles import Analyse, Correctif, EtatFaille, Faille

journal = logging.getLogger("patchproof.livraison")
API_GITHUB = "https://api.github.com"


def _correctifs_livres(analyse: Analyse) -> list[tuple[Faille, Correctif]]:
    """Correctifs acceptés (validés et non rejetés par le développeur), avec leur test de preuve."""
    paires = []
    for faille in analyse.failles:
        if faille.etat != EtatFaille.corrigee:
            continue
        correctif = next((c for c in faille.correctifs if c.valide and c.decision != "rejete"), None)
        if correctif:
            paires.append((faille, correctif))
    return paires


def generer_patch(analyse: Analyse) -> str:
    """Patch unifié rassemblant les correctifs acceptés et leurs tests de non-régression."""
    morceaux = []
    for faille, correctif in _correctifs_livres(analyse):
        morceaux.append(f"# {faille.fichier}:{faille.ligne} — {faille.famille.value} ({faille.cwe})\n")
        morceaux.append(correctif.diff.rstrip("\n") + "\n")
        if faille.test_preuve:
            morceaux.append(_diff_ajout_fichier(faille.test_preuve.chemin, faille.test_preuve.contenu))
    return "\n".join(morceaux) if morceaux else "# Aucun correctif accepté à livrer.\n"


def _diff_ajout_fichier(chemin: str, contenu: str) -> str:
    lignes = contenu.splitlines()
    corps = "".join(f"+{l}\n" for l in lignes)
    return (
        f"diff --git a/{chemin} b/{chemin}\nnew file mode 100644\n--- /dev/null\n+++ b/{chemin}\n"
        f"@@ -0,0 +1,{len(lignes)} @@\n{corps}"
    )


def ouvrir_pull_request(s: Session, analyse: Analyse, jeton_github: str,
                        branche: str | None, titre: str | None) -> str:
    projet = analyse.projet
    if projet.source != "github" or not projet.url_github:
        raise ValueError("La pull request n'est disponible que pour un projet importé depuis GitHub.")
    proprietaire, depot = projet.url_github.rstrip("/").split("/")[-2:]
    depot = depot.removesuffix(".git")
    entetes = {"Authorization": f"Bearer {jeton_github}", "Accept": "application/vnd.github+json"}
    branche = branche or f"patchproof/analyse-{analyse.id}"

    with httpx.Client(base_url=API_GITHUB, headers=entetes, timeout=30) as client:
        info = client.get(f"/repos/{proprietaire}/{depot}").json()
        base = info["default_branch"]
        sha_base = client.get(f"/repos/{proprietaire}/{depot}/git/ref/heads/{base}").json()["object"]["sha"]
        client.post(f"/repos/{proprietaire}/{depot}/git/refs",
                    json={"ref": f"refs/heads/{branche}", "sha": sha_base})

        for faille, correctif in _correctifs_livres(analyse):
            _committer_fichier(client, proprietaire, depot, branche, faille.fichier,
                               _appliquer(correctif.diff), f"fix({faille.famille.value}): {faille.fichier}")
            if faille.test_preuve:
                _committer_fichier(client, proprietaire, depot, branche, faille.test_preuve.chemin,
                                   faille.test_preuve.contenu, f"test: preuve pour {faille.fichier}")

        pr = client.post(f"/repos/{proprietaire}/{depot}/pulls", json={
            "title": titre or f"PatchProof — {len(_correctifs_livres(analyse))} correctifs prouvés",
            "head": branche, "base": base,
            "body": _corps_pr(analyse),
        }).json()
    url = pr.get("html_url")
    if not url:
        raise ValueError(f"GitHub a refusé la pull request : {pr.get('message', 'erreur inconnue')}")
    return url


def _committer_fichier(client, proprietaire, depot, branche, chemin, contenu, message) -> None:
    actuel = client.get(f"/repos/{proprietaire}/{depot}/contents/{chemin}", params={"ref": branche})
    sha = actuel.json().get("sha") if actuel.status_code == 200 else None
    corps = {"message": message, "branch": branche,
             "content": base64.b64encode(contenu.encode()).decode()}
    if sha:
        corps["sha"] = sha
    client.put(f"/repos/{proprietaire}/{depot}/contents/{chemin}", json=corps)


def _appliquer(diff: str) -> str:
    """Reconstruit le contenu final d'un fichier à partir des lignes conservées et ajoutées du diff."""
    lignes = []
    for ligne in diff.splitlines():
        if ligne.startswith(("diff ", "index ", "--- ", "+++ ", "@@", "new file", "deleted file")):
            continue
        if ligne.startswith("+"):
            lignes.append(ligne[1:])
        elif ligne.startswith("-"):
            continue
        elif ligne.startswith(" "):
            lignes.append(ligne[1:])
    return "\n".join(lignes) + "\n"


def _corps_pr(analyse: Analyse) -> str:
    lignes = ["Correctifs générés par PatchProof, chacun prouvé par un test de non-régression.", ""]
    for faille, _ in _correctifs_livres(analyse):
        lignes.append(f"- `{faille.fichier}:{faille.ligne}` — {faille.famille.value} ({faille.cwe})")
    return "\n".join(lignes)
