"""Classification des règles des scanners en familles du périmètre (E-2.2)."""

from pathlib import Path

from patchproof.core.modeles import Famille
from patchproof.detection.familles import (
    est_regle_audit,
    famille_bandit,
    famille_depuis_bandit,
    famille_depuis_cwe,
    famille_semgrep,
)
from patchproof.detection.scanners import extrait_source


def test_familles_bandit_assertives():
    assert famille_bandit("B608", "89") == Famille.sqli
    assert famille_bandit("B602", "78") == Famille.commande
    assert famille_bandit("B105", "259") == Famille.secret


def test_notes_audit_ecartees():
    """B404, B603 et B607 ne constatent pas une vulnérabilité : elles ne créent pas d'alerte.

    B603 et B607 réapparaissent à la même ligne qu'un B602 dès que le correctif remplace
    shell=True par une liste d'arguments : sans cette exclusion, la 3e condition de validation
    (« l'alerte a disparu ») échouerait sur tout correctif d'injection de commandes.
    """
    for regle in ("B404", "B603", "B607"):
        assert est_regle_audit(regle)
        assert famille_depuis_bandit(regle) is None
        assert famille_bandit(regle, "78") is None


def test_repli_sur_le_cwe_pour_une_regle_inconnue():
    assert famille_bandit("B999", "89") == Famille.sqli
    assert famille_bandit("B999", "") is None


def test_familles_semgrep_par_nom_de_regle():
    """Le nom de la règle est prioritaire : les métadonnées CWE du registre sont imprécises.

    `tainted-sql-string` annonce CWE-704 (conversion de type) alors qu'elle décrit une injection
    SQL : sans cette correspondance, l'alerte serait écartée du périmètre.
    """
    assert famille_semgrep("tainted-sql-string", "CWE-704") == Famille.sqli
    assert famille_semgrep("path-traversal-open", "CWE-22") == Famille.traversee
    assert famille_semgrep("subprocess-injection", "CWE-78") == Famille.commande
    assert famille_semgrep("regle-inconnue", "CWE-798") == Famille.secret
    assert famille_semgrep("regle-inconnue", "CWE-999") is None


def test_cwe_259_est_un_secret():
    """Bandit attribue CWE-259 aux secrets codés en dur, en plus de CWE-798."""
    assert famille_depuis_cwe("CWE-259") == Famille.secret


def test_extrait_source(tmp_path: Path):
    (tmp_path / "app.py").write_text("ligne1\nligne2\nligne3\nfaille\nligne5\nligne6\nligne7\n",
                                     encoding="utf-8")
    extrait = extrait_source(tmp_path, "app.py", 4)
    assert "4 | faille" in extrait
    assert "2 | ligne2" in extrait          # contexte de 2 lignes avant
    assert "6 | ligne6" in extrait          # et de 2 lignes après


def test_extrait_source_cas_limites(tmp_path: Path):
    (tmp_path / "app.py").write_text("seule ligne\n", encoding="utf-8")
    assert extrait_source(tmp_path, "absent.py", 3) == ""
    assert extrait_source(tmp_path, "app.py", 99) == ""
    assert extrait_source(tmp_path, "", 3) == ""
    assert extrait_source(tmp_path, "app.py", 0) == ""
    assert "seule ligne" in extrait_source(tmp_path, "app.py", 1)
