"""Tables PostgreSQL (voir docs/modele-donnees.md)."""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from patchproof.core.db import Base


def maintenant() -> datetime:
    return datetime.now(UTC)


class Role(StrEnum):
    developpeur = "developpeur"
    responsable_securite = "responsable_securite"
    administrateur = "administrateur"


class EtatAnalyse(StrEnum):
    en_attente = "en_attente"
    preparation = "preparation"
    detection = "detection"
    selection = "selection"
    traitement = "traitement"
    en_pause = "en_pause"
    terminee = "terminee"
    echec = "echec"


class EtatFaille(StrEnum):
    en_attente = "en_attente"
    en_cours = "en_cours"
    confirmee = "confirmee"
    faux_positif = "faux_positif"
    corrigee = "corrigee"
    revue_humaine = "revue_humaine"


ETATS_FINAUX = {EtatFaille.faux_positif, EtatFaille.corrigee, EtatFaille.revue_humaine}


class Famille(StrEnum):
    sqli = "sqli"            # CWE-89
    commande = "commande"    # CWE-78
    secret = "secret"        # CWE-798
    traversee = "traversee"  # CWE-22


class Utilisateur(Base):
    __tablename__ = "utilisateurs"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    nom: Mapped[str] = mapped_column(String(120))
    mot_de_passe_hash: Mapped[str] = mapped_column(String(100))
    role: Mapped[Role] = mapped_column(String(30), default=Role.developpeur)
    actif: Mapped[bool] = mapped_column(Boolean, default=True)
    github_jeton_chiffre: Mapped[str | None] = mapped_column(Text, nullable=True)
    github_login: Mapped[str | None] = mapped_column(String(100), nullable=True)
    cree_le: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=maintenant)

    projets: Mapped[list["Projet"]] = relationship(back_populates="proprietaire")


class Projet(Base):
    __tablename__ = "projets"

    id: Mapped[int] = mapped_column(primary_key=True)
    proprietaire_id: Mapped[int] = mapped_column(ForeignKey("utilisateurs.id", ondelete="CASCADE"))
    nom: Mapped[str] = mapped_column(String(200))
    source: Mapped[str] = mapped_column(String(10))  # github | zip
    url_github: Mapped[str | None] = mapped_column(String(300), nullable=True)
    commit_sha: Mapped[str | None] = mapped_column(String(40), nullable=True)
    chemin_stockage: Mapped[str] = mapped_column(String(400))
    framework: Mapped[str | None] = mapped_column(String(20), nullable=True)
    commande_test: Mapped[str | None] = mapped_column(String(200), nullable=True)
    nb_lignes: Mapped[int] = mapped_column(Integer, default=0)
    cree_le: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=maintenant)

    proprietaire: Mapped[Utilisateur] = relationship(back_populates="projets")
    analyses: Mapped[list["Analyse"]] = relationship(
        back_populates="projet", cascade="all, delete-orphan", order_by="Analyse.id.desc()"
    )


class Analyse(Base):
    __tablename__ = "analyses"

    id: Mapped[int] = mapped_column(primary_key=True)
    projet_id: Mapped[int] = mapped_column(ForeignKey("projets.id", ondelete="CASCADE"), index=True)
    etat: Mapped[EtatAnalyse] = mapped_column(String(20), default=EtatAnalyse.en_attente)
    jetons_utilises: Mapped[int] = mapped_column(Integer, default=0)
    cout_estime_usd: Mapped[float] = mapped_column(Float, default=0.0)
    message_erreur: Mapped[str | None] = mapped_column(Text, nullable=True)
    parametres: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    cree_le: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=maintenant)
    termine_le: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    projet: Mapped[Projet] = relationship(back_populates="analyses")
    failles: Mapped[list["Faille"]] = relationship(
        back_populates="analyse", cascade="all, delete-orphan", order_by="Faille.priorite"
    )


class Faille(Base):
    __tablename__ = "failles"

    id: Mapped[int] = mapped_column(primary_key=True)
    analyse_id: Mapped[int] = mapped_column(ForeignKey("analyses.id", ondelete="CASCADE"), index=True)
    outils: Mapped[str] = mapped_column(String(40))
    regle: Mapped[str] = mapped_column(String(200))
    fichier: Mapped[str] = mapped_column(String(400))
    ligne: Mapped[int] = mapped_column(Integer)
    cwe: Mapped[str] = mapped_column(String(20))
    famille: Mapped[Famille] = mapped_column(String(20))
    gravite: Mapped[str] = mapped_column(String(10))
    exposee: Mapped[bool] = mapped_column(Boolean, default=False)
    priorite: Mapped[int] = mapped_column(Integer, default=0)
    extrait: Mapped[str] = mapped_column(Text, default="")
    exclue: Mapped[bool] = mapped_column(Boolean, default=False)
    etat: Mapped[EtatFaille] = mapped_column(String(20), default=EtatFaille.en_attente)
    point_entree: Mapped[str | None] = mapped_column(String(300), nullable=True)
    justification: Mapped[str | None] = mapped_column(Text, nullable=True)
    tentatives_attaque: Mapped[int] = mapped_column(Integer, default=0)
    tentatives_defense: Mapped[int] = mapped_column(Integer, default=0)
    decision_revue: Mapped[str | None] = mapped_column(String(40), nullable=True)
    commentaire_revue: Mapped[str | None] = mapped_column(Text, nullable=True)

    analyse: Mapped[Analyse] = relationship(back_populates="failles")
    test_preuve: Mapped["TestPreuve | None"] = relationship(
        back_populates="faille", cascade="all, delete-orphan", uselist=False
    )
    correctifs: Mapped[list["Correctif"]] = relationship(
        back_populates="faille", cascade="all, delete-orphan", order_by="Correctif.tentative"
    )

    @property
    def identifiant(self) -> str:
        """Identifiant lisible utilisé dans les échanges avec les agents (ex. B608-app.py-42)."""
        return f"{self.regle.split('.')[-1]}-{self.fichier.split('/')[-1]}-{self.ligne}"


class TestPreuve(Base):
    __tablename__ = "tests_preuve"
    __test__ = False  # pas une classe de test pytest

    id: Mapped[int] = mapped_column(primary_key=True)
    faille_id: Mapped[int] = mapped_column(ForeignKey("failles.id", ondelete="CASCADE"), unique=True)
    chemin: Mapped[str] = mapped_column(String(400))
    contenu: Mapped[str] = mapped_column(Text)
    sortie: Mapped[str] = mapped_column(Text, default="")

    faille: Mapped[Faille] = relationship(back_populates="test_preuve")


class Correctif(Base):
    __tablename__ = "correctifs"

    id: Mapped[int] = mapped_column(primary_key=True)
    faille_id: Mapped[int] = mapped_column(ForeignKey("failles.id", ondelete="CASCADE"), index=True)
    tentative: Mapped[int] = mapped_column(Integer)
    diff: Mapped[str] = mapped_column(Text)
    explication: Mapped[str] = mapped_column(Text, default="")
    valide: Mapped[bool] = mapped_column(Boolean, default=False)
    resultat_validation: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    decision: Mapped[str] = mapped_column(String(12), default="en_attente")

    faille: Mapped[Faille] = relationship(back_populates="correctifs")


class EtapeAgent(Base):
    __tablename__ = "etapes_agent"

    id: Mapped[int] = mapped_column(primary_key=True)
    analyse_id: Mapped[int] = mapped_column(ForeignKey("analyses.id", ondelete="CASCADE"), index=True)
    faille_id: Mapped[int | None] = mapped_column(
        ForeignKey("failles.id", ondelete="CASCADE"), nullable=True, index=True
    )
    agent: Mapped[str] = mapped_column(String(15))
    nature: Mapped[str] = mapped_column(String(20))
    resume: Mapped[str] = mapped_column(Text, default="")
    outil: Mapped[str | None] = mapped_column(String(40), nullable=True)
    arguments: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    resultat: Mapped[str | None] = mapped_column(Text, nullable=True)
    succes: Mapped[bool] = mapped_column(Boolean, default=True)
    jetons_entree: Mapped[int] = mapped_column(Integer, default=0)
    jetons_sortie: Mapped[int] = mapped_column(Integer, default=0)
    cree_le: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=maintenant)


class ParametresAdmin(Base):
    """Une seule ligne (id = 1), initialisée depuis .env au premier démarrage."""

    __tablename__ = "parametres"

    id: Mapped[int] = mapped_column(primary_key=True)
    budget_jetons_analyse: Mapped[int] = mapped_column(Integer)
    max_tentatives_agent: Mapped[int] = mapped_column(Integer)
    max_appels_outils_faille: Mapped[int] = mapped_column(Integer)
    modele_attaquant: Mapped[str] = mapped_column(String(100))
    modele_defenseur: Mapped[str] = mapped_column(String(100))
    modele_leger: Mapped[str] = mapped_column(String(100))
