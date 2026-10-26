"""Relance d'une analyse interrompue (M5).

Régression : une analyse dont la tâche a été abandonnée — conteneur redémarré pendant l'analyse —
restait bloquée dans son dernier état. L'interface attendait alors indéfiniment, sans moyen de
repartir, et une relance naïve aurait de plus enregistré deux fois les mêmes alertes.
"""

import io
import zipfile

import pytest

from patchproof.core.db import session
from patchproof.core.modeles import Analyse, EtatAnalyse, Faille, Famille
from patchproof.orchestration.analyse import _reinitialiser_alertes
from tests.conftest import entetes

PREPARATION = "patchproof.orchestration.analyse.preparer_et_detecter"
TRAITEMENT = "patchproof.orchestration.analyse.traiter_analyse"

PROJET_FLASK = {
    "app.py": "from flask import Flask\napp = Flask(__name__)\n",
    "requirements.txt": "flask\n",
    "tests/test_app.py": "def test_ok():\n    assert True\n",
}


class FausseFile:
    """File RQ factice : enregistre les tâches qui auraient été mises en file."""

    def __init__(self) -> None:
        self.taches: list[tuple[str, tuple, dict]] = []

    def enqueue(self, fonction: str, *args, **kwargs) -> None:
        self.taches.append((fonction, args, kwargs))

    @property
    def fonctions(self) -> list[str]:
        return [t[0] for t in self.taches]


@pytest.fixture
def file_factice(monkeypatch) -> FausseFile:
    fausse = FausseFile()
    monkeypatch.setattr("patchproof.orchestration.routes.file", lambda: fausse)
    return fausse


def _zip_projet() -> bytes:
    flux = io.BytesIO()
    with zipfile.ZipFile(flux, "w") as archive:
        for nom, contenu in PROJET_FLASK.items():
            archive.writestr(nom, contenu)
    return flux.getvalue()


def _creer_analyse(client) -> tuple[dict[str, str], int]:
    entetes_ = entetes(client)
    projet = client.post("/api/projets/zip", headers=entetes_,
                         files={"fichier": ("p.zip", _zip_projet(), "application/zip")}).json()
    analyse = client.post(f"/api/projets/{projet['id']}/analyses", headers=entetes_).json()
    return entetes_, analyse["id"]


def _changer_etat(analyse_id: int, etat: EtatAnalyse) -> None:
    with session() as s:
        s.get(Analyse, analyse_id).etat = etat


def test_la_creation_d_analyse_met_en_file_la_preparation(client, file_factice):
    _creer_analyse(client)
    assert file_factice.fonctions == [PREPARATION]


@pytest.mark.parametrize("etat, tache", [
    (EtatAnalyse.preparation, PREPARATION),
    (EtatAnalyse.detection, PREPARATION),
    (EtatAnalyse.echec, PREPARATION),
    (EtatAnalyse.traitement, TRAITEMENT),
    (EtatAnalyse.en_pause, TRAITEMENT),
])
def test_la_relance_reprend_la_phase_interrompue(client, file_factice, etat, tache):
    entetes_, analyse_id = _creer_analyse(client)
    _changer_etat(analyse_id, etat)
    file_factice.taches.clear()

    reponse = client.post(f"/api/analyses/{analyse_id}/relancer", headers=entetes_)

    assert reponse.status_code == 202, reponse.text
    assert file_factice.fonctions == [tache]


def test_relance_refusee_si_l_analyse_attend_la_selection(client, file_factice):
    entetes_, analyse_id = _creer_analyse(client)
    _changer_etat(analyse_id, EtatAnalyse.selection)
    file_factice.taches.clear()

    reponse = client.post(f"/api/analyses/{analyse_id}/relancer", headers=entetes_)

    assert reponse.status_code == 422
    assert "sélection" in reponse.json()["detail"]
    assert file_factice.taches == []


def test_relance_refusee_si_l_analyse_est_terminee(client, file_factice):
    entetes_, analyse_id = _creer_analyse(client)
    _changer_etat(analyse_id, EtatAnalyse.terminee)

    reponse = client.post(f"/api/analyses/{analyse_id}/relancer", headers=entetes_)

    assert reponse.status_code == 422
    assert "terminée" in reponse.json()["detail"]


def test_reinitialisation_des_alertes_evite_les_doublons(client, file_factice):
    """Une relance de la détection repart d'une liste d'alertes propre."""
    _, analyse_id = _creer_analyse(client)
    with session() as s:
        analyse = s.get(Analyse, analyse_id)
        for ligne in range(1, 4):
            analyse.failles.append(Faille(outils="bandit", regle="B608", fichier="app.py", ligne=ligne,
                                          cwe="CWE-89", famille=Famille.sqli, gravite="haute"))
        analyse.message_erreur = "interrompue"
        s.flush()

    with session() as s:
        analyse = s.get(Analyse, analyse_id)
        assert len(analyse.failles) == 3
        _reinitialiser_alertes(analyse)
        s.flush()
        assert analyse.failles == []
        assert analyse.message_erreur is None
