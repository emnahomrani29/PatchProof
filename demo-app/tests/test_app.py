"""Tests du comportement normal de l'application de démonstration.

Ces tests ne vérifient que le fonctionnement attendu, jamais un comportement anormal : ils
doivent rester au vert avant l'analyse *et* après application des correctifs de PatchProof.
"""

import os

import pytest

from app import app


@pytest.fixture
def client():
    app.config.update(TESTING=True)
    with app.test_client() as c:
        yield c


def test_accueil(client):
    reponse = client.get("/")
    assert reponse.status_code == 200
    assert reponse.get_json()["service"] == "annuaire-demo"


def test_liste_utilisateurs(client):
    reponse = client.get("/users")
    assert reponse.status_code == 200
    assert [u["nom"] for u in reponse.get_json()] == ["alice", "bob", "carol"]


def test_recherche_utilisateur_existant(client):
    reponse = client.get("/users/search?nom=alice")
    assert reponse.status_code == 200
    trouves = reponse.get_json()
    assert len(trouves) == 1 and trouves[0]["email"] == "alice@exemple.tn"


def test_recherche_sans_resultat(client):
    assert client.get("/users/search?nom=personne").get_json() == []


def test_statistiques(client):
    reponse = client.get("/stats")
    assert reponse.status_code == 200
    assert reponse.get_json()["visites"] == 3


def test_conditions_generales(client):
    reponse = client.get("/docs/cgu")
    assert reponse.status_code == 200
    assert reponse.data.decode().strip() == "Conditions générales."


def test_document_inconnu(client):
    assert client.get("/docs/inconnu").status_code == 404


def test_telechargement_document_public(client):
    reponse = client.get("/download?fichier=cgu.txt")
    assert reponse.status_code == 200
    assert "Conditions générales." in reponse.data.decode()


@pytest.mark.skipif(os.name != "posix", reason="cette route s'appuie sur cat, présent sous Linux")
def test_rapport_ventes(client):
    reponse = client.get("/report?nom=ventes")
    assert reponse.status_code == 200
    assert b"1200" in reponse.data


def test_rapport_inconnu(client):
    assert client.get("/report?nom=inconnu").status_code == 400


def test_whoami(client):
    reponse = client.get("/whoami")
    assert reponse.status_code == 200
    assert reponse.get_json()["service"] == "annuaire-demo"
