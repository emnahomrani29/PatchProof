"""Outils exposés aux agents par appel de fonction (docs/agents.md §2).

Chaque outil déclare ses paramètres avec un modèle Pydantic, validé avant l'exécution.
Les lectures et écritures se font dans la copie de travail du worker. L'exécution de code
(pytest) passe uniquement par le bac à sable.
"""

import fnmatch
import re
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel, Field

from patchproof.core.git import ErreurGit, git
from patchproof.core.interfaces import Bac

MAX_LIGNES_LECTURE = 400
MAX_RESULTATS_RECHERCHE = 50
MAX_SORTIE = 4_000
DOSSIER_TESTS_SECURITE = "tests/security"
DOSSIERS_IGNORES = {".git", ".venv", "venv", "node_modules", "__pycache__", ".pytest_cache"}


class OutilRefuse(Exception):
    """Appel refusé : le message est renvoyé tel quel à l'agent."""


@dataclass
class Outil:
    nom: str
    description: str
    parametres: type[BaseModel]
    fonction: Callable[[Bac, BaseModel], str]

    def definition(self) -> dict:
        schema = self.parametres.model_json_schema()
        schema.pop("title", None)
        return {
            "type": "function",
            "function": {"name": self.nom, "description": self.description, "parameters": schema},
        }


def chemin_sur(racine: Path, relatif: str) -> Path:
    """Résout un chemin relatif à la racine du projet et refuse toute sortie de celle-ci."""
    if not relatif or Path(relatif).is_absolute() or ".." in Path(relatif).parts:
        raise OutilRefuse(f"Chemin refusé : {relatif!r}. Donnez un chemin relatif à la racine du projet.")
    cible = (racine / relatif).resolve()
    if not cible.is_relative_to(racine.resolve()):
        raise OutilRefuse(f"Chemin refusé : {relatif!r} sort du projet.")
    return cible


def tronquer(texte: str, limite: int = MAX_SORTIE) -> str:
    if len(texte) <= limite:
        return texte
    moitie = limite // 2
    return f"{texte[:moitie]}\n[… {len(texte) - limite} caractères omis …]\n{texte[-moitie:]}"


# --- lire_fichier ----------------------------------------------------------------


class ParamsLire(BaseModel):
    chemin: str = Field(description="Chemin relatif à la racine du projet, ex. app/routes.py")
    debut: int = Field(default=1, ge=1, description="Première ligne (incluse)")
    fin: int | None = Field(default=None, ge=1, description="Dernière ligne (incluse)")


def lire_fichier(bac: Bac, p: ParamsLire) -> str:
    cible = chemin_sur(bac.racine, p.chemin)
    if not cible.is_file():
        raise OutilRefuse(f"Fichier introuvable : {p.chemin}")
    lignes = cible.read_text(encoding="utf-8", errors="replace").splitlines()
    fin = min(p.fin or len(lignes), p.debut + MAX_LIGNES_LECTURE - 1, len(lignes))
    extrait = [f"{n:>5} | {lignes[n - 1]}" for n in range(p.debut, fin + 1)]
    suite = f"\n[… {len(lignes) - fin} lignes restantes]" if fin < len(lignes) else ""
    return f"{p.chemin} (lignes {p.debut}-{fin} sur {len(lignes)})\n" + "\n".join(extrait) + suite


# --- chercher_code ---------------------------------------------------------------


class ParamsChercher(BaseModel):
    motif: str = Field(min_length=1, max_length=200, description="Expression régulière Python")
    glob: str = Field(default="*.py", max_length=100, description="Filtre sur le nom de fichier, ex. *.py")


def _fichiers(racine: Path, glob: str):
    for chemin in sorted(racine.rglob("*")):
        relatif = chemin.relative_to(racine)
        if chemin.is_file() and not DOSSIERS_IGNORES.intersection(relatif.parts) \
                and fnmatch.fnmatch(chemin.name, glob):
            yield chemin, relatif.as_posix()


def chercher_code(bac: Bac, p: ParamsChercher) -> str:
    try:
        motif = re.compile(p.motif)
    except re.error:
        motif = re.compile(re.escape(p.motif))
    resultats: list[str] = []
    for chemin, relatif in _fichiers(bac.racine, p.glob):
        for n, ligne in enumerate(chemin.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            if motif.search(ligne[:500]):
                resultats.append(f"{relatif}:{n}: {ligne.strip()[:200]}")
                if len(resultats) >= MAX_RESULTATS_RECHERCHE:
                    return "\n".join(resultats) + "\n[limite de 50 résultats atteinte]"
    return "\n".join(resultats) or "Aucun résultat."


# --- ecrire_test (Attaquant uniquement) ----------------------------------------


class ParamsEcrireTest(BaseModel):
    nom: str = Field(pattern=r"^[a-z0-9_]{3,60}$", description="Suffixe du fichier : tests/security/test_<nom>.py")
    contenu: str = Field(min_length=20, max_length=20_000, description="Code pytest complet du fichier")


def ecrire_test(bac: Bac, p: ParamsEcrireTest) -> str:
    try:
        compile(p.contenu, f"test_{p.nom}.py", "exec")  # analyse syntaxique seulement, rien n'est exécuté
    except SyntaxError as e:
        raise OutilRefuse(f"Erreur de syntaxe ligne {e.lineno} : {e.msg}. Le fichier n'a pas été écrit.") from e
    relatif = f"{DOSSIER_TESTS_SECURITE}/test_{p.nom}.py"
    cible = chemin_sur(bac.racine, relatif)
    cible.parent.mkdir(parents=True, exist_ok=True)
    cible.write_text(p.contenu, encoding="utf-8")
    return f"Test écrit : {relatif}"


# --- appliquer_diff (Défenseur uniquement) -------------------------------------


class ParamsDiff(BaseModel):
    diff: str = Field(min_length=10, max_length=30_000, description="Diff unifié (--- a/… +++ b/…)")


_ENTETE_DIFF = re.compile(r"^(?:---|\+\+\+) (?:[ab]/)?(\S+)", re.MULTILINE)


# Fichiers qui changent ce que pytest exécute ou les dépendances installées (hors périmètre v1).
FICHIERS_PROTEGES = {"conftest.py", "pytest.ini", "tox.ini", "setup.cfg", "pyproject.toml",
                     "requirements.txt", "requirements-dev.txt"}


def fichier_protege(relatif: str) -> bool:
    parties = Path(relatif).parts
    return "tests" in parties or (bool(parties) and parties[-1] in FICHIERS_PROTEGES)


def fichiers_du_diff(diff: str) -> set[str]:
    return {f for f in _ENTETE_DIFF.findall(diff) if f != "/dev/null"}


def appliquer_diff(bac: Bac, p: ParamsDiff) -> str:
    fichiers = fichiers_du_diff(p.diff)
    if not fichiers:
        raise OutilRefuse("Diff illisible : en-têtes '--- a/chemin' et '+++ b/chemin' attendus.")
    for f in fichiers:
        chemin_sur(bac.racine, f)
        if fichier_protege(f):
            raise OutilRefuse(f"Interdit : le Défenseur ne modifie ni les tests ni leur configuration ({f}).")
    texte = p.diff if p.diff.endswith("\n") else p.diff + "\n"
    with tempfile.NamedTemporaryFile("w", suffix=".diff", delete=False, encoding="utf-8") as fichier:
        fichier.write(texte)
    options = ["apply", "--recount", "--whitespace=nowarn"]
    try:
        try:
            git(bac.racine, *options, "--check", fichier.name)
        except ErreurGit:
            options.append("-C1")  # contexte réduit : tolère un décalage des lignes de contexte
            git(bac.racine, *options, "--check", fichier.name)
        git(bac.racine, *options, fichier.name)
    except ErreurGit as e:
        raise OutilRefuse(f"Le diff ne s'applique pas : {tronquer(str(e), 800)}") from e
    finally:
        Path(fichier.name).unlink(missing_ok=True)
    return f"Diff appliqué sur : {', '.join(sorted(fichiers))}"


# --- remplacer (Défenseur uniquement) -----------------------------------------
# Édition par recherche/remplacement exact : bien plus fiable qu'un diff unifié pour un LLM, qui
# calcule souvent de mauvais numéros de ligne. L'orchestrateur relit le diff réel (git diff) ensuite.


class ParamsRemplacer(BaseModel):
    chemin: str = Field(description="Fichier à modifier, relatif à la racine du projet")
    ancien: str = Field(min_length=1, max_length=20_000,
                        description="Texte exact à remplacer (doit apparaître une seule fois)")
    nouveau: str = Field(max_length=20_000, description="Texte de remplacement")


def remplacer(bac: Bac, p: ParamsRemplacer) -> str:
    if fichier_protege(p.chemin):
        raise OutilRefuse(f"Interdit : le Défenseur ne modifie ni les tests ni leur configuration ({p.chemin}).")
    cible = chemin_sur(bac.racine, p.chemin)
    if not cible.is_file():
        raise OutilRefuse(f"Fichier introuvable : {p.chemin}")
    contenu = cible.read_text(encoding="utf-8", errors="replace")
    occurrences = contenu.count(p.ancien)
    if occurrences == 0:
        raise OutilRefuse("Texte à remplacer introuvable tel quel. Relis le fichier et recopie-le exactement "
                          "(indentation et espaces compris).")
    if occurrences > 1:
        raise OutilRefuse(f"Texte ambigu : trouvé {occurrences} fois. Donne un extrait plus long et unique.")
    cible.write_text(contenu.replace(p.ancien, p.nouveau, 1), encoding="utf-8")
    return f"Remplacement effectué dans {p.chemin}."


# --- executer_tests --------------------------------------------------------------


class ParamsTests(BaseModel):
    cible: str | None = Field(
        default=None, max_length=200,
        description="Fichier ou test à lancer (ex. tests/security/test_x.py). Vide = tous les tests",
    )


def executer_tests(bac: Bac, p: ParamsTests) -> str:
    commande = ["python", "-m", "pytest", "-q", "--no-header", "-p", "no:cacheprovider", "-rfE"]
    if p.cible:
        chemin_sur(bac.racine, p.cible.split("::")[0])
        commande.append(p.cible)
    bac.synchroniser()
    resultat = bac.executer(commande)
    if resultat.delai_depasse:
        return "Délai de 120 s dépassé : les tests ont été interrompus."
    return f"Code retour pytest : {resultat.code_retour}\n{tronquer(resultat.sortie)}"


OUTILS: dict[str, Outil] = {
    o.nom: o
    for o in [
        Outil("lire_fichier", "Lit un fichier du projet avec numéros de ligne (400 lignes au plus).",
              ParamsLire, lire_fichier),
        Outil("chercher_code", "Cherche une expression régulière dans les fichiers du projet.",
              ParamsChercher, chercher_code),
        Outil("ecrire_test", "Écrit un test pytest dans tests/security/test_<nom>.py.",
              ParamsEcrireTest, ecrire_test),
        Outil("remplacer", "Remplace un extrait de code exact par un autre (hors tests/). À privilégier.",
              ParamsRemplacer, remplacer),
        Outil("appliquer_diff", "Applique un diff unifié au code de l'application (hors tests/).",
              ParamsDiff, appliquer_diff),
        Outil("executer_tests", "Lance pytest dans le bac à sable et renvoie le résultat.",
              ParamsTests, executer_tests),
    ]
}

OUTILS_ATTAQUANT = ["lire_fichier", "chercher_code", "ecrire_test", "executer_tests"]
OUTILS_DEFENSEUR = ["lire_fichier", "chercher_code", "remplacer", "appliquer_diff", "executer_tests"]
