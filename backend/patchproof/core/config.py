"""Configuration lue depuis les variables d'environnement (fichier .env en développement)."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Parametres(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # LLM
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    modele_attaquant: str = "anthropic/claude-sonnet-5.5"
    modele_defenseur: str = "anthropic/claude-sonnet-5.5"
    modele_leger: str = "anthropic/claude-haiku-5.5"
    delai_appel_llm: float = 60.0
    attentes_nouvelles_tentatives: tuple[float, ...] = (1.0, 4.0, 16.0)

    # Limites par défaut
    budget_jetons_analyse: int = 400_000
    max_tentatives_agent: int = 3
    max_appels_outils_faille: int = 30

    # Bac à sable
    image_sandbox: str = "patchproof-sandbox:latest"
    memoire_sandbox: str = "2g"
    delai_execution: int = 120
    max_lignes_projet: int = 5_000

    # Sécurité
    jwt_secret: str = "dev-uniquement"
    jwt_duree_heures: int = 12
    cle_chiffrement: str = ""

    # GitHub
    github_client_id: str = ""
    github_client_secret: str = ""

    # Infrastructure
    database_url: str = "postgresql+psycopg://patchproof:patchproof@localhost:5432/patchproof"
    redis_url: str = "redis://localhost:6379/0"
    url_frontend: str = "http://localhost:5173"
    url_api: str = "http://localhost:8000"
    dossier_donnees: Path = Path("data")
    dossier_prompts: Path = Path(__file__).resolve().parents[3] / "prompts"

    @property
    def dossier_projets(self) -> Path:
        return self.dossier_donnees / "projets"


@lru_cache
def parametres() -> Parametres:
    return Parametres()
