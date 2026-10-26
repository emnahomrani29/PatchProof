"""Validation d'un correctif en 3 conditions + anti-triche (docs/agents.md, E-5.2).

Un correctif est accepté seulement si :
  1. le test de preuve échoue désormais (la faille n'est plus exploitable) ;
  2. tous les tests existants passent encore ;
  3. le scanner ne signale plus l'alerte sur le fichier corrigé.
Plus deux garde-fous : le dossier tests/ est resté intact, et le diff appliqué est non vide.
"""

import hashlib
from pathlib import Path

from patchproof.core.interfaces import Bac
from patchproof.core.schemas import Alerte, ResultatValidation
from patchproof.detection.scanners import lancer_scanners

DOSSIER_TESTS = "tests"


def empreinte_tests(racine: Path) -> str:
    """Empreinte du contenu du dossier tests/, pour détecter toute modification par le Défenseur."""
    h = hashlib.sha256()
    dossier = racine / DOSSIER_TESTS
    if dossier.is_dir():
        for chemin in sorted(dossier.rglob("*")):
            if chemin.is_file() and "__pycache__" not in chemin.parts:
                h.update(chemin.relative_to(racine).as_posix().encode())
                h.update(chemin.read_bytes())
    return h.hexdigest()


def valider_correctif(
    bac: Bac,
    alerte: Alerte,
    test_fichier: str,
    diff: str,
    empreinte_tests_avant: str,
    commande_test: str,
) -> ResultatValidation:
    bac.synchroniser()

    # Garde-fou 1 : le diff doit exister.
    if not diff.strip():
        return ResultatValidation(diff_applique=False, tests_intacts=True, preuve_bloquee=False,
                                  tests_existants_ok=False, alerte_disparue=False,
                                  message="Aucune modification de code proposée.")

    # Garde-fou 2 : le dossier tests/ n'a pas bougé.
    tests_intacts = empreinte_tests(bac.racine) == empreinte_tests_avant
    if not tests_intacts:
        return ResultatValidation(diff_applique=True, tests_intacts=False, preuve_bloquee=False,
                                  tests_existants_ok=False, alerte_disparue=False,
                                  message="Le dossier tests/ a été modifié : correctif rejeté.")

    # Condition 1 : le test de preuve doit maintenant ÉCHOUER.
    preuve = bac.executer(["python", "-m", "pytest", "-q", "--no-header", "-p", "no:cacheprovider", test_fichier])
    preuve_bloquee = not preuve.delai_depasse and preuve.code_retour != 0

    # Condition 2 : les tests existants (hors tests/security) doivent passer.
    existants = bac.executer([*commande_test.split(), "--ignore=tests/security", "-q", "-p", "no:cacheprovider"])
    tests_existants_ok = not existants.delai_depasse and existants.code_retour == 0

    # Condition 3 : le scanner ne signale plus l'alerte sur ce fichier/cette ligne.
    alerte_disparue = not _alerte_presente(bac, alerte)

    message = _message(preuve_bloquee, tests_existants_ok, alerte_disparue)
    return ResultatValidation(
        diff_applique=True, tests_intacts=True, preuve_bloquee=preuve_bloquee,
        tests_existants_ok=tests_existants_ok, alerte_disparue=alerte_disparue, message=message,
        sorties={"preuve": preuve.sortie[-2000:], "tests_existants": existants.sortie[-2000:]},
    )


def _alerte_presente(bac: Bac, alerte: Alerte) -> bool:
    for trouvee in lancer_scanners(bac):
        if trouvee.fichier == alerte.fichier and abs(trouvee.ligne - alerte.ligne) <= 2 \
                and (trouvee.famille == alerte.famille or trouvee.regle == alerte.regle):
            return True
    return False


def _message(preuve: bool, existants: bool, alerte: bool) -> str:
    if preuve and existants and alerte:
        return "Correctif validé : faille bloquée, tests au vert, alerte disparue."
    manques = []
    if not preuve:
        manques.append("le test de preuve réussit encore (faille toujours exploitable)")
    if not existants:
        manques.append("des tests existants échouent (régression)")
    if not alerte:
        manques.append("le scanner signale encore l'alerte")
    return "Correctif refusé : " + " ; ".join(manques) + "."
