"""Worker d'analyse : `python -m patchproof.worker` (service `worker` de docker compose)."""

import logging

from redis import Redis
from rq import Queue, Worker

from patchproof.core.config import parametres
from patchproof.core.db import creer_tables

FILE_ANALYSES = "analyses"


def file_analyses() -> Queue:
    return Queue(FILE_ANALYSES, connection=Redis.from_url(parametres().redis_url))


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s : %(message)s")
    creer_tables()
    connexion = Redis.from_url(parametres().redis_url)
    # Une seule analyse à la fois (docs/decisions.md, D-10)
    Worker([Queue(FILE_ANALYSES, connection=connexion)], connection=connexion).work()


if __name__ == "__main__":
    main()
