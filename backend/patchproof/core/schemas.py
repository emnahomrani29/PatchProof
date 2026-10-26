"""Types échangés entre modules et avec le frontend (voir docs/modules.md et docs/api.md)."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from patchproof.core.modeles import EtatAnalyse, EtatFaille, Famille, Role

# --- Échanges entre modules -------------------------------------------------


class ResultatCommande(BaseModel):
    code_retour: int
    sortie: str
    delai_depasse: bool = False

    @property
    def succes(self) -> bool:
        return self.code_retour == 0 and not self.delai_depasse


class InfoProjet(BaseModel):
    framework: Literal["flask", "fastapi"] | None
    commande_test: str = "python -m pytest -q"
    nb_lignes: int
    a_des_tests: bool


class ResultatTests(BaseModel):
    reussis: int = 0
    echoues: int = 0
    erreurs: int = 0
    sortie: str = ""

    @property
    def tous_passent(self) -> bool:
        return self.echoues == 0 and self.erreurs == 0 and self.reussis > 0


class AlerteBrute(BaseModel):
    """Alerte telle que produite par un scanner, avant normalisation."""

    outil: Literal["bandit", "semgrep"]
    donnees: dict


class Alerte(BaseModel):
    """Format commun après normalisation (E-2.1)."""

    outils: list[str]
    regle: str
    fichier: str
    ligne: int
    cwe: str
    famille: Famille | None = None
    gravite: Literal["haute", "moyenne", "basse"]
    extrait: str = ""
    exposee: bool = False
    priorite: int = 0


class VerdictAttaquant(BaseModel):
    """Sortie finale de l'agent Attaquant."""

    alerte_id: str
    verdict: Literal["confirmee", "faux_positif"]
    point_entree: str | None = None
    test_fichier: str | None = Field(default=None, pattern=r"^tests/security/test_[\w]+\.py$")
    justification: str = Field(min_length=10, max_length=1500)


class PropositionCorrectif(BaseModel):
    """Sortie finale de l'agent Défenseur. Le diff de référence est relu dans l'espace de travail (git diff)."""

    alerte_id: str
    explication: str = Field(min_length=10, max_length=1500)


class ResultatValidation(BaseModel):
    diff_applique: bool
    tests_intacts: bool
    preuve_bloquee: bool
    tests_existants_ok: bool
    alerte_disparue: bool
    message: str = ""
    sorties: dict[str, str] = {}

    @property
    def accepte(self) -> bool:
        return (
            self.diff_applique
            and self.tests_intacts
            and self.preuve_bloquee
            and self.tests_existants_ok
            and self.alerte_disparue
        )


NatureEtape = Literal[
    "raisonnement", "appel_outil", "resultat_outil", "verdict", "validation", "erreur", "information",
]
NomAgent = Literal["attaquant", "defenseur", "orchestrateur"]


class Etape(BaseModel):
    """Une étape du suivi en direct, enregistrée puis diffusée."""

    analyse_id: int
    faille_id: int | None = None
    agent: NomAgent
    nature: NatureEtape
    resume: str
    outil: str | None = None
    arguments: dict | None = None
    resultat: str | None = None
    succes: bool = True
    jetons_entree: int = 0
    jetons_sortie: int = 0


# --- API : entrées ------------------------------------------------------------


class Inscription(BaseModel):
    email: EmailStr
    nom: str = Field(min_length=2, max_length=120)
    mot_de_passe: str = Field(min_length=8, max_length=128)


class Connexion(BaseModel):
    email: EmailStr
    mot_de_passe: str


class NouveauProjetGithub(BaseModel):
    url_github: str = Field(pattern=r"^https://github\.com/[\w.-]+/[\w.-]+/?$")


class ModifFaille(BaseModel):
    exclue: bool


class DecisionCorrectif(BaseModel):
    decision: Literal["accepte", "rejete"]


class DecisionRevue(BaseModel):
    decision: Literal["corrigee_manuellement", "faux_positif", "acceptee_risque"]
    commentaire: str = Field(min_length=3, max_length=2000)


class ModifUtilisateur(BaseModel):
    role: Role | None = None
    actif: bool | None = None


class ParametresSortie(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    budget_jetons_analyse: int = Field(ge=10_000, le=5_000_000)
    max_tentatives_agent: int = Field(ge=1, le=10)
    max_appels_outils_faille: int = Field(ge=5, le=100)
    modele_attaquant: str
    modele_defenseur: str
    modele_leger: str


class DemandePullRequest(BaseModel):
    branche: str | None = Field(default=None, pattern=r"^[\w./-]{1,100}$")
    titre: str | None = Field(default=None, max_length=200)


# --- API : sorties ------------------------------------------------------------


class UtilisateurSortie(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    nom: str
    role: Role
    actif: bool
    github_login: str | None = None


class JetonSortie(BaseModel):
    jeton: str
    utilisateur: UtilisateurSortie


class ProjetSortie(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nom: str
    source: str
    url_github: str | None
    framework: str | None
    commande_test: str | None
    nb_lignes: int
    cree_le: datetime


class Compteurs(BaseModel):
    total: int = 0
    exclues: int = 0
    en_attente: int = 0
    confirmees: int = 0
    faux_positifs: int = 0
    corrigees: int = 0
    revue_humaine: int = 0


class AnalyseSortie(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    projet_id: int
    etat: EtatAnalyse
    jetons_utilises: int
    cout_estime_usd: float
    message_erreur: str | None
    cree_le: datetime
    termine_le: datetime | None
    compteurs: Compteurs = Compteurs()


class FailleSortie(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    outils: str
    regle: str
    fichier: str
    ligne: int
    cwe: str
    famille: Famille
    gravite: str
    exposee: bool
    priorite: int
    extrait: str
    exclue: bool
    etat: EtatFaille
    point_entree: str | None
    justification: str | None
    tentatives_attaque: int
    tentatives_defense: int
    decision_revue: str | None
    commentaire_revue: str | None


class EtapeSortie(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    faille_id: int | None
    agent: str
    nature: str
    resume: str
    outil: str | None
    resultat: str | None
    succes: bool
    cree_le: datetime
