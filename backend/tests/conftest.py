import pytest


@pytest.fixture
def client(tmp_path, monkeypatch):
    """Application complète sur une base SQLite temporaire."""
    from fastapi.testclient import TestClient

    from patchproof.core import config, db

    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'test.db'}")
    monkeypatch.setenv("DOSSIER_DONNEES", str(tmp_path / "donnees"))
    monkeypatch.setenv("JWT_SECRET", "secret-de-test")
    config.parametres.cache_clear()
    db.moteur.cache_clear()
    db._fabrique.cache_clear()

    from patchproof.api.app import app

    with TestClient(app) as c:
        yield c

    config.parametres.cache_clear()
    db.moteur.cache_clear()
    db._fabrique.cache_clear()


def entetes(client, email="dev@exemple.com") -> dict[str, str]:
    client.post("/api/auth/inscription", json={"email": email, "nom": "Dev", "mot_de_passe": "motdepasse123"})
    jeton = client.post("/api/auth/connexion", json={"email": email, "mot_de_passe": "motdepasse123"}).json()["jeton"]
    return {"Authorization": f"Bearer {jeton}"}
