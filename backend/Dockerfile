FROM python:3.12-slim

# git : clonage des dépôts et application des diffs (git apply), sans exécuter le code du projet.
# Bibliothèques Pango : export PDF du rapport (WeasyPrint).
RUN apt-get update \
    && apt-get install -y --no-install-recommends git libpango-1.0-0 libpangoft2-1.0-0 fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml .
COPY patchproof ./patchproof
RUN pip install --no-cache-dir -e ".[rapport,dev]"

ENV PYTHONUNBUFFERED=1 \
    DOSSIER_PROMPTS=/app/prompts \
    DOSSIER_DONNEES=/data

EXPOSE 8000
CMD ["uvicorn", "patchproof.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
