"""Les colonnes d'énumération doivent se relire en objets Python, pas en chaînes.

Régression : les colonnes étaient déclarées `Mapped[EtatAnalyse]` mais créées en `String`, donc une
valeur relue depuis la base restait une chaîne. Le suivi en direct (`analyse.etat.value`), le rapport
(`analyse.etat.value`, `faille.famille.value`) et la livraison échouaient alors en AttributeError.
L'erreur n'apparaissait pas dans le worker, qui venait d'affecter le membre en mémoire.
"""

from patchproof.core.db import session
from patchproof.core.modeles import (
    Analyse,
    EtatAnalyse,
    EtatFaille,
    Faille,
    Famille,
    Projet,
    Role,
    Utilisateur,
)


def _creer_une_faille() -> tuple[int, int, int]:
    with session() as s:
        utilisateur = Utilisateur(email="relu@exemple.tn", nom="Relu", mot_de_passe_hash="h")
        s.add(utilisateur)
        s.flush()
        projet = Projet(proprietaire_id=utilisateur.id, nom="p", source="zip", chemin_stockage="/tmp")
        s.add(projet)
        s.flush()
        analyse = Analyse(projet_id=projet.id)
        s.add(analyse)
        s.flush()
        faille = Faille(analyse_id=analyse.id, outils="bandit", regle="B608", fichier="app.py", ligne=1,
                        cwe="CWE-89", famille=Famille.sqli, gravite="haute")
        s.add(faille)
        s.flush()
        return utilisateur.id, analyse.id, faille.id


def test_les_etats_relus_en_base_sont_des_enum(client):
    id_utilisateur, id_analyse, id_faille = _creer_une_faille()

    with session() as s:
        utilisateur = s.get(Utilisateur, id_utilisateur)
        analyse = s.get(Analyse, id_analyse)
        faille = s.get(Faille, id_faille)

        assert isinstance(utilisateur.role, Role) and utilisateur.role is Role.developpeur
        assert isinstance(analyse.etat, EtatAnalyse) and analyse.etat is EtatAnalyse.en_attente
        assert isinstance(faille.etat, EtatFaille) and faille.etat is EtatFaille.en_attente
        assert isinstance(faille.famille, Famille) and faille.famille is Famille.sqli

        # Ce que lisent le suivi en direct, le rapport et le patch.
        assert analyse.etat.value == "en_attente"
        assert faille.etat.value == "en_attente"
        assert faille.famille.value == "sqli"


def test_la_valeur_stockee_est_le_texte_attendu(client):
    """La base doit contenir « en_attente », pas le nom du membre d'énumération."""
    from sqlalchemy import text

    _creer_une_faille()
    with session() as s:
        etat = s.execute(text("SELECT etat FROM analyses")).scalar_one()
        famille = s.execute(text("SELECT famille FROM failles")).scalar_one()
    assert etat == "en_attente"
    assert famille == "sqli"
