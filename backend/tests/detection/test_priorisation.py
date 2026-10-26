from pathlib import Path

from patchproof.core.modeles import Famille
from patchproof.core.schemas import Alerte
from patchproof.detection.familles import famille_depuis_bandit, famille_depuis_cwe
from patchproof.detection.priorisation import fusionner, prioriser


def alerte(**kw):
    base = {
        "outils": ["bandit"], "regle": "B608", "fichier": "app.py", "ligne": 42, "cwe": "CWE-89",
        "famille": Famille.sqli, "gravite": "haute", "extrait": "x",
    }
    base.update(kw)
    return Alerte(**base)


def test_familles():
    assert famille_depuis_cwe("CWE-89") == Famille.sqli
    assert famille_depuis_cwe("22") == Famille.traversee
    assert famille_depuis_cwe("CWE-999") is None
    assert famille_depuis_bandit("B602") == Famille.commande


def test_fusion_doublons():
    a = alerte(outils=["bandit"], extrait="court")
    b = alerte(outils=["semgrep"], gravite="moyenne", extrait="extrait plus long")
    fusion = fusionner([a, b])
    assert len(fusion) == 1
    assert fusion[0].outils == ["bandit", "semgrep"]
    assert fusion[0].gravite == "haute"              # on garde la plus grave
    assert fusion[0].extrait == "extrait plus long"  # on garde le plus informatif


def test_fusion_garde_les_alertes_distinctes():
    a = alerte(ligne=42)
    b = alerte(ligne=99)
    assert len(fusionner([a, b])) == 2


def test_priorisation_filtre_et_trie(tmp_path: Path):
    (tmp_path / "routes.py").write_text("@app.route('/u')\ndef u():\n    pass\n", encoding="utf-8")
    (tmp_path / "utils.py").write_text("def aide():\n    pass\n", encoding="utf-8")
    alertes = [
        alerte(fichier="utils.py", gravite="basse", famille=Famille.secret),
        alerte(fichier="routes.py", gravite="basse", famille=Famille.sqli),
        alerte(fichier="routes.py", gravite="haute", famille=Famille.commande),
        alerte(fichier="autre.py", famille=None),  # hors périmètre, doit disparaître
    ]
    resultat = prioriser(alertes, tmp_path)
    assert all(a.famille is not None for a in resultat)
    assert len(resultat) == 3
    assert resultat[0].gravite == "haute"                  # gravité d'abord
    assert resultat[1].exposee and not resultat[2].exposee  # puis exposition
    assert [a.priorite for a in resultat] == [1, 2, 3]
