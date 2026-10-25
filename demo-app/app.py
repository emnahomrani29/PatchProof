"""Petite application Flask servant de cible d'analyse à PatchProof.

Application de démonstration : elle contient volontairement des défauts de sécurité, comme un
projet repris sans audit. Elle ne doit jamais être déployée ni exposée sur un réseau ; elle
s'exécute uniquement dans le bac à sable de PatchProof ou via le client de test Flask.
"""

import os
import sqlite3
import subprocess

from flask import Flask, abort, g, jsonify, request

app = Flask(__name__)

DOSSIER_RACINE = os.path.dirname(os.path.abspath(__file__))
BASE_DONNEES = os.path.join(DOSSIER_RACINE, "demo.sqlite3")
DOSSIER_DOCS = os.path.join(DOSSIER_RACINE, "docs_publics")

# Jeton utilisé par les scripts de synchronisation internes.
API_TOKEN = "sk_demo_9f4b7c21e8a34d5f6b0c1e2d3a4b5c6d"

# Rapports disponibles dans le dossier des documents publics.
RAPPORTS = {"ventes": "sales.txt", "trafic": "traffic.txt"}
# Documents publics consultables sans authentification.
DOCS_AUTORISES = {"cgu", "mentions", "aide"}


def connexion():
    if "db" not in g:
        g.db = sqlite3.connect(BASE_DONNEES)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def fermer_connexion(_exception):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def initialiser_base():
    """Crée la base SQLite et un petit jeu de données au premier démarrage."""
    db = sqlite3.connect(BASE_DONNEES)
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS utilisateurs (
            id INTEGER PRIMARY KEY, nom TEXT, email TEXT, role TEXT
        );
        CREATE TABLE IF NOT EXISTS visites (
            id INTEGER PRIMARY KEY, page TEXT, compte INTEGER
        );
        """
    )
    if db.execute("SELECT COUNT(*) FROM utilisateurs").fetchone()[0] == 0:
        db.executemany(
            "INSERT INTO utilisateurs (nom, email, role) VALUES (?, ?, ?)",
            [
                ("alice", "alice@exemple.tn", "admin"),
                ("bob", "bob@exemple.tn", "utilisateur"),
                ("carol", "carol@exemple.tn", "utilisateur"),
            ],
        )
        db.executemany(
            "INSERT INTO visites (page, compte) VALUES (?, ?)",
            [("/", 120), ("/users", 45), ("/docs/cgu", 18)],
        )
    db.commit()
    db.close()


@app.route("/")
def accueil():
    return jsonify(
        service="annuaire-demo",
        version="1.0",
        routes=["/users", "/users/search", "/stats", "/ping", "/download", "/docs/<nom>", "/report"],
    )


@app.route("/users")
def lister_utilisateurs():
    lignes = connexion().execute("SELECT id, nom, email FROM utilisateurs ORDER BY id").fetchall()
    return jsonify([dict(ligne) for ligne in lignes])


@app.route("/users/search")
def chercher_utilisateur():
    nom = request.args.get("nom", "")
    lignes = connexion().execute(
        "SELECT id, nom, email FROM utilisateurs WHERE nom = '" + nom + "'"
    ).fetchall()
    return jsonify([dict(ligne) for ligne in lignes])


@app.route("/stats")
def statistiques():
    db = connexion()
    total = db.execute("SELECT COUNT(*) FROM visites").fetchone()[0]
    pages = db.execute("SELECT page, compte FROM visites ORDER BY compte DESC").fetchall()
    return jsonify(visites=total, pages=[dict(page) for page in pages])


@app.route("/ping")
def ping():
    """Diagnostic réseau : vérifie que l'hôte indiqué répond."""
    hote = request.args.get("host", "127.0.0.1")
    return subprocess.check_output("ping -c 1 " + hote, shell=True)


@app.route("/download")
def telecharger():
    """Renvoie le contenu d'un document public du dossier des documents."""
    nom = request.args.get("fichier", "")
    with open(os.path.join(DOSSIER_DOCS, nom), encoding="utf-8") as fichier:
        return fichier.read()


@app.route("/docs/<nom>")
def document(nom):
    """Renvoie un document public par son nom court, sans extension."""
    if nom not in DOCS_AUTORISES:
        abort(404)
    with open(os.path.join(DOSSIER_DOCS, nom + ".txt"), encoding="utf-8") as fichier:
        return fichier.read()


@app.route("/report")
def rapport():
    """Renvoie le rapport d'activité préparé par le back-office."""
    cle = request.args.get("nom", "ventes")
    if cle not in RAPPORTS:
        abort(400)
    return subprocess.check_output(f"cat {RAPPORTS[cle]}", shell=True)


@app.route("/whoami")
def identite():
    return jsonify(authentifie=bool(API_TOKEN), service="annuaire-demo")


initialiser_base()


if __name__ == "__main__":
    app.run(port=5000)
