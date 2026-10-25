"""Connexion PostgreSQL et sessions SQLAlchemy."""

from collections.abc import Iterator
from contextlib import contextmanager
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from patchproof.core.config import parametres


class Base(DeclarativeBase):
    pass


@lru_cache
def moteur() -> Engine:
    url = parametres().database_url
    # psycopg3 prépare côté serveur les requêtes répétées. Quand une connexion du pool est
    # réutilisée (fréquent dans le worker qui enregistre beaucoup d'étapes), le même nom de requête
    # préparée entre en conflit (« prepared statement _pg3_0 already exists »). On désactive la
    # préparation automatique pour les bases psycopg.
    connect_args = {"prepare_threshold": None} if url.startswith("postgresql+psycopg") else {}
    return create_engine(url, pool_pre_ping=True, connect_args=connect_args)


@lru_cache
def _fabrique() -> sessionmaker[Session]:
    return sessionmaker(bind=moteur(), expire_on_commit=False)


@contextmanager
def session() -> Iterator[Session]:
    """Session transactionnelle : commit en fin de bloc, rollback en cas d'exception."""
    s = _fabrique()()
    try:
        yield s
        s.commit()
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()


def session_requete() -> Iterator[Session]:
    """Dépendance FastAPI : une session par requête HTTP."""
    with session() as s:
        yield s


def creer_tables() -> None:
    from patchproof.core import modeles  # noqa: F401  (enregistre les tables)

    Base.metadata.create_all(moteur())
