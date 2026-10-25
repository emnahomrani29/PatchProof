"""Lancement de Bandit et Semgrep dans le bac à sable, et normalisation des alertes (E-2.1).

Les scanners tournent dans le conteneur isolé (pas de réseau, règles Semgrep embarquées).
Leurs sorties JSON sont lues côté worker, puis converties dans un format commun.
"""

import json
import logging

from patchproof.core.interfaces import Bac
from patchproof.core.schemas import Alerte
from patchproof.detection.familles import famille_depuis_bandit, famille_depuis_cwe

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


def _bandit(bac: Bac) -> list[Alerte]:
    res = bac.executer(["bandit", "-r", ".", "-f", "json", "-q"], delai=180)
    donnees = _json_sortie(res.sortie)
    if donnees is None:
        journal.warning("Bandit : sortie illisible (code %s)", res.code_retour)
        return []
    alertes = []
    for r in donnees.get("results", []):
        cwe = str((r.get("issue_cwe") or {}).get("id") or "")
        famille = famille_depuis_cwe(cwe) or famille_depuis_bandit(r.get("test_id", ""))
        alertes.append(Alerte(
            outils=["bandit"],
            regle=r.get("test_id", "bandit"),
            fichier=_relatif(r.get("filename", "")),
            ligne=r.get("line_number", 0),
            cwe=f"CWE-{cwe}" if cwe else "",
            famille=famille,
            gravite=GRAVITE_BANDIT.get(r.get("issue_severity", ""), "basse"),
            extrait=(r.get("code") or "").strip()[:500],
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
        meta = extra.get("metadata", {})
        cwe = _premier_cwe(meta.get("cwe"))
        alertes.append(Alerte(
            outils=["semgrep"],
            regle=r.get("check_id", "semgrep").split(".")[-1],
            fichier=_relatif(r.get("path", "")),
            ligne=(r.get("start") or {}).get("line", 0),
            cwe=cwe,
            famille=famille_depuis_cwe(cwe),
            gravite=GRAVITE_SEMGREP.get(extra.get("severity", ""), "basse"),
            extrait=(extra.get("lines") or "").strip()[:500],
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
