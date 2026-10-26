# Image du bac à sable : un conteneur par analyse, créé par le worker (docs/securite.md §2).
FROM python:3.12-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl coreutils \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir pytest pytest-timeout coverage bandit semgrep

# Règles Semgrep téléchargées à la construction : l'analyse se fait ensuite sans réseau (D-07).
RUN mkdir -p /regles \
    && curl -fsSL https://semgrep.dev/c/p/python -o /regles/python.yml \
    && curl -fsSL https://semgrep.dev/c/p/flask -o /regles/flask.yml
COPY regles/ /regles/locales/

RUN useradd --create-home --uid 1000 analyse \
    && mkdir -p /projet && chown analyse:analyse /projet
USER analyse
WORKDIR /projet

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    SEMGREP_SEND_METRICS=off \
    PATH="/home/analyse/.local/bin:${PATH}"

CMD ["sleep", "infinity"]
