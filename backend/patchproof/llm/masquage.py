"""Masquage des secrets et données personnelles avant tout envoi au LLM (docs/securite.md §1).

Une même valeur reçoit toujours le même marqueur pendant une analyse, ce qui permet de
rétablir les valeurs d'origine dans les réponses (ex. lignes de contexte d'un diff).
"""

import re

_MOTIFS_JETONS = [
    ("CLE_PRIVEE", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]+?-----END [A-Z ]*PRIVATE KEY-----")),
    ("SECRET", re.compile(r"\bsk-(?:or-|proj-|ant-)?[A-Za-z0-9_-]{20,}")),
    ("SECRET", re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{30,}|\bgithub_pat_[A-Za-z0-9_]{40,}")),
    ("SECRET", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("SECRET", re.compile(r"\bxox[abpr]-[A-Za-z0-9-]{10,}")),
    ("SECRET", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}")),
    ("EMAIL", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")),
    ("TEL", re.compile(r"(?<![\w.])\+\d{1,3}[ .-]?\d{1,4}(?:[ .-]?\d{2,4}){2,4}\b")),
    ("TEL", re.compile(r"(?<![\w.])0[1-9](?:[ .-]\d{2}){4}\b")),
]

# Littéral affecté à un nom qui évoque un secret : password = "…", "api_key": "…"
_MOTIF_AFFECTATION = re.compile(
    r"""(?ix)
    (?P<nom>\b[\w-]*(?:password|passwd|pwd|secret|token|api_?key|access_?key|private_?key|credential)[\w-]*)
    (?P<sep>["']?\s*[:=]\s*[bru]?)
    (?P<guillemet>["'])(?P<valeur>[^"'\n]{4,})(?P=guillemet)
    """
)

_MARQUEUR = re.compile(r"<(?:SECRET|CLE_PRIVEE|EMAIL|TEL)_\d+>")


class Masqueur:
    def __init__(self) -> None:
        self._valeur_vers_marqueur: dict[str, str] = {}
        self._marqueur_vers_valeur: dict[str, str] = {}
        self._compteurs: dict[str, int] = {}

    def _marqueur(self, categorie: str, valeur: str) -> str:
        if valeur in self._valeur_vers_marqueur:
            return self._valeur_vers_marqueur[valeur]
        self._compteurs[categorie] = self._compteurs.get(categorie, 0) + 1
        marqueur = f"<{categorie}_{self._compteurs[categorie]}>"
        self._valeur_vers_marqueur[valeur] = marqueur
        self._marqueur_vers_valeur[marqueur] = valeur
        return marqueur

    def masquer(self, texte: str) -> str:
        if not texte:
            return texte

        def remplacer_affectation(m: re.Match) -> str:
            valeur = m.group("valeur")
            if _MARQUEUR.fullmatch(valeur) or valeur.startswith(("$", "{", "%(")):
                return m.group(0)
            return f"{m.group('nom')}{m.group('sep')}{m.group('guillemet')}" \
                   f"{self._marqueur('SECRET', valeur)}{m.group('guillemet')}"

        texte = _MOTIF_AFFECTATION.sub(remplacer_affectation, texte)
        for categorie, motif in _MOTIFS_JETONS:
            texte = motif.sub(lambda m, c=categorie: self._marqueur(c, m.group(0)), texte)
        # Une valeur déjà connue peut réapparaître ailleurs sans contexte d'affectation.
        for valeur, marqueur in sorted(self._valeur_vers_marqueur.items(), key=lambda kv: -len(kv[0])):
            if len(valeur) >= 6:
                texte = texte.replace(valeur, marqueur)
        return texte

    def demasquer(self, texte: str) -> str:
        if not texte or not self._marqueur_vers_valeur:
            return texte
        return _MARQUEUR.sub(lambda m: self._marqueur_vers_valeur.get(m.group(0), m.group(0)), texte)

    @property
    def valeurs_masquees(self) -> set[str]:
        return set(self._valeur_vers_marqueur)
