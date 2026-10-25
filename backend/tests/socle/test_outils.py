import pytest

from patchproof.agents.outils import (
    OutilRefuse,
    ParamsChercher,
    ParamsDiff,
    ParamsEcrireTest,
    ParamsLire,
    ParamsTests,
    appliquer_diff,
    chemin_sur,
    chercher_code,
    ecrire_test,
    executer_tests,
    lire_fichier,
)
from tests.factices import FauxBac

APP = "def route(nom):\n    return 'Bonjour ' + nom\n"


@pytest.fixture
def bac(tmp_path):
    (tmp_path / "app.py").write_text(APP, encoding="utf-8")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_app.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    return FauxBac(tmp_path)


@pytest.mark.parametrize("chemin", ["../secret.txt", "/etc/passwd", "a/../../b", ""])
def test_chemins_hors_projet_refuses(bac, chemin):
    with pytest.raises(OutilRefuse):
        chemin_sur(bac.racine, chemin)


def test_lire_fichier_numerote(bac):
    sortie = lire_fichier(bac, ParamsLire(chemin="app.py"))
    assert "    2 |     return 'Bonjour ' + nom" in sortie


def test_chercher_code(bac):
    assert "app.py:2:" in chercher_code(bac, ParamsChercher(motif=r"Bonjour"))
    assert chercher_code(bac, ParamsChercher(motif="introuvable")) == "Aucun résultat."


def test_ecrire_test_refuse_la_syntaxe_invalide(bac):
    with pytest.raises(OutilRefuse, match="syntaxe"):
        ecrire_test(bac, ParamsEcrireTest(nom="preuve", contenu="def test_x(:\n    pass\n" * 2))
    assert not (bac.racine / "tests" / "security").exists()


def test_ecrire_test_dans_tests_security(bac):
    ecrire_test(bac, ParamsEcrireTest(nom="preuve", contenu="def test_preuve():\n    assert 1 + 1 == 2\n"))
    assert (bac.racine / "tests" / "security" / "test_preuve.py").is_file()


DIFF_APP = """--- a/app.py
+++ b/app.py
@@ -1,2 +1,2 @@
 def route(nom):
-    return 'Bonjour ' + nom
+    return 'Bonjour ' + nom.strip()
"""


def test_appliquer_diff(bac):
    appliquer_diff(bac, ParamsDiff(diff=DIFF_APP))
    assert "nom.strip()" in (bac.racine / "app.py").read_text(encoding="utf-8")


@pytest.mark.parametrize("fichier", ["tests/test_app.py", "conftest.py", "pytest.ini"])
def test_diff_sur_les_tests_refuse(bac, fichier):
    diff = DIFF_APP.replace("app.py", fichier)
    with pytest.raises(OutilRefuse, match="Interdit"):
        appliquer_diff(bac, ParamsDiff(diff=diff))


def test_diff_qui_ne_s_applique_pas(bac):
    with pytest.raises(OutilRefuse, match="ne s'applique pas"):
        appliquer_diff(bac, ParamsDiff(diff=DIFF_APP.replace("def route(nom):", "def autre():")))


def test_executer_tests_passe_par_le_bac(bac):
    sortie = executer_tests(bac, ParamsTests(cible="tests/test_app.py"))
    assert bac.synchronisations == 1
    assert bac.commandes[0][:3] == ["python", "-m", "pytest"]
    assert bac.commandes[0][-1] == "tests/test_app.py"
    assert "Code retour pytest : 0" in sortie
