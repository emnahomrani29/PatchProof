"""Lancement de Bandit et Semgrep dans le bac à sable, et normalisation des alertes (E-2.1).

Les scanners tournent dans le conteneur isolé (pas de réseau, règles Semgrep embarquées).
Leurs sorties JSON sont lues côté worker, puis converties dans un format commun.
"""

import json
import logging
from pathlib import Path

from patchproof.core.interfaces import Bac
from patchproof.core.schemas import Alerte
from patchproof.detection.familles import famille_bandit, famille_semgrep

journal = logging.getLogger("patchproof.detection")

GRAVITE_BANDIT = {"HIGH": "haute", "MEDIUM": "moyenne", "LOW": "basse"}
GRAVITE_SEMGREP = {"ERROR": "haute", "WARNING": "moyenne", "INFO": "basse"}


def lancer_scanners(bac: Bac) -> list[Alerte]:
    bac.synchroniser()
    return _bandit(bac) + _semgrep(bac)


def _json_sortie(sortie: str) -> dict | None:
    debut = sortie.find("{")
    if debut < 0:
        return None
    try:
        return json.loads(sortie[debut:])
    except json.JSONDecodeError:
        return None


def extrait_source(racine: Path, chemin: str, ligne: int, contexte: int = 2) -> str:
    """Lignes de code autour de l'alerte, numérotées comme l'outil `lire_fichier`.

    Aucun des deux scanners ne fournit d'extrait exploitable : le champ `lines` de Semgrep
    contient l'annotation de la règle (« requires login » dans le paquet du registre) et non le
    code. On relit donc le fichier du projet, ce qui garantit à l'agent un extrait fidèle.
    """
    if not chemin or ligne <= 0:
        return ""
    try:
        lignes = (racine / chemin).read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return ""
    if ligne > len(lignes):
        return ""
    debut = max(1, ligne - contexte)
    fin = min(len(lignes), ligne + contexte)
    return "\n".join(f"{n:>5} | {lignes[n - 1]}" for n in range(debut, fin + 1))[:500]


def _bandit(bac: Bac) -> list[Alerte]:
    res = bac.executer(["bandit", "-r", ".", "-f", "json", "-q"], delai=180)
    donnees = _json_sortie(res.sortie)
    if donnees is None:
        journal.warning("Bandit : sortie illisible (code %s)", res.code_retour)
        return []
    alertes = []
    for r in donnees.get("results", []):
        cwe = str((r.get("issue_cwe") or {}).get("id") or "")
        fichier = _relatif(r.get("filename", ""))
        ligne = r.get("line_number", 0)
        alertes.append(Alerte(
            outils=["bandit"],
            regle=r.get("test_id", "bandit"),
            fichier=fichier,
            ligne=ligne,
            cwe=f"CWE-{cwe}" if cwe else "",
            famille=famille_bandit(r.get("test_id"), cwe),
            gravite=GRAVITE_BANDIT.get(r.get("issue_severity", ""), "basse"),
            extrait=extrait_source(bac.racine, fichier, ligne) or (r.get("code") or "").strip()[:500],
        ))
    return alertes


def _semgrep(bac: Bac) -> list[Alerte]:
    res = bac.executer(
        ["semgrep", "--config", "/regles", "--json", "--quiet", "--no-git-ignore", "."], delai=240,
    )
    donnees = _json_sortie(res.sortie)
    if donnees is None:
        journal.warning("Semgrep : sortie illisible (code %s)", res.code_retour)
        return []
    alertes = []
    for r in donnees.get("results", []):
        extra = r.get("extra", {})
        regle = r.get("check_id", "semgrep").split(".")[-1]
        cwe = _premier_cwe(extra.get("metadata", {}).get("cwe"))
        fichier = _relatif(r.get("path", ""))
        ligne = (r.get("start") or {}).get("line", 0)
        alertes.append(Alerte(
            outils=["semgrep"],
            regle=regle,
            fichier=fichier,
            ligne=ligne,
            cwe=cwe,
            famille=famille_semgrep(regle, cwe),
            gravite=GRAVITE_SEMGREP.get(extra.get("severity", ""), "basse"),
            extrait=extrait_source(bac.racine, fichier, ligne),
        ))
    return alertes


def _premier_cwe(valeur) -> str:
    if isinstance(valeur, list):
        valeur = valeur[0] if valeur else ""
    texte = str(valeur or "")
    debut = texte.upper().find("CWE-")
    if debut < 0:
        return ""
    numero = ""
    for c in texte[debut + 4:]:
        if c.isdigit():
            numero += c
        else:
            break
    return f"CWE-{numero}" if numero else ""


def _relatif(chemin: str) -> str:
    chemin = chemin.replace("\\", "/")
    for prefixe in ("/projet/", "./"):
        chemin = chemin.removeprefix(prefixe)
    return chemin.lstrip("/")
