import io
import zipfile

from tests.conftest import entetes


def zip_projet(fichiers: dict[str, str]) -> bytes:
    flux = io.BytesIO()
    with zipfile.ZipFile(flux, "w") as z:
        for nom, contenu in fichiers.items():
            z.writestr(nom, contenu)
    return flux.getvalue()


FLASK = {
    "projet-main/app.py": "from flask import Flask\napp = Flask(__name__)\n\n@app.route('/')\ndef index():\n    return 'ok'\n",
    "projet-main/requirements.txt": "flask\n",
    "projet-main/tests/test_app.py": "def test_ok():\n    assert True\n",
}


def test_inscription_connexion_moi(client):
    h = entetes(client)
    moi = client.get("/api/auth/moi", headers=h).json()
    assert moi["email"] == "dev@exemple.com"
    assert moi["role"] == "administrateur"  # premier compte


def test_second_compte_developpeur(client):
    entetes(client)
    h2 = entetes(client, "autre@exemple.com")
    assert client.get("/api/auth/moi", headers=h2).json()["role"] == "developpeur"


def test_mauvais_mot_de_passe(client):
    entetes(client)
    r = client.post("/api/auth/connexion", json={"email": "dev@exemple.com", "mot_de_passe": "faux-faux"})
    assert r.status_code == 401 and r.json()["code"] == "non_authentifie"


def test_routes_protegees(client):
    assert client.get("/api/projets").status_code == 401


def test_import_zip_flask(client):
    h = entetes(client)
    r = client.post("/api/projets/zip", headers=h,
                    files={"fichier": ("projet.zip", zip_projet(FLASK), "application/zip")})
    assert r.status_code == 201, r.text
    projet = r.json()
    assert projet["framework"] == "flask" and projet["nb_lignes"] > 0
    assert [p["id"] for p in client.get("/api/projets", headers=h).json()] == [projet["id"]]


def test_zip_sans_framework_refuse(client):
    h = entetes(client)
    r = client.post("/api/projets/zip", headers=h,
                    files={"fichier": ("p.zip", zip_projet({"main.py": "print('hello')\n"}), "application/zip")})
    assert r.status_code == 422 and r.json()["code"] == "framework_non_supporte"


def test_zip_avec_chemin_dangereux_refuse(client):
    h = entetes(client)
    r = client.post("/api/projets/zip", headers=h,
                    files={"fichier": ("p.zip", zip_projet({"../evasion.py": "x = 1\n"}), "application/zip")})
    assert r.status_code == 422 and r.json()["code"] == "zip_invalide"


def test_projet_d_un_autre_utilisateur_interdit(client):
    h1 = entetes(client)
    pid = client.post("/api/projets/zip", headers=h1,
                      files={"fichier": ("p.zip", zip_projet(FLASK), "application/zip")}).json()["id"]
    h2 = entetes(client, "autre@exemple.com")
    assert client.get(f"/api/projets/{pid}", headers=h2).status_code == 403


def test_administration_reservee(client):
    h_admin = entetes(client)
    h_dev = entetes(client, "autre@exemple.com")
    assert client.get("/api/admin/parametres", headers=h_dev).status_code == 403
    params = client.get("/api/admin/parametres", headers=h_admin).json()
    params["max_tentatives_agent"] = 2
    assert client.put("/api/admin/parametres", headers=h_admin, json=params).json()["max_tentatives_agent"] == 2
