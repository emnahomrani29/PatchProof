"""Objets factices partagés par les tests : bac à sable et API LLM simulés (rien n'est exécuté)."""

import json
from collections.abc import Callable
from pathlib import Path
from types import SimpleNamespace

from patchproof.core.schemas import ResultatCommande


class FauxBac:
    """Bac à sable simulé : enregistre les commandes et renvoie des résultats prédéfinis."""

    def __init__(self, racine: Path, reponses: Callable[[list[str]], ResultatCommande] | None = None):
        self.racine = racine
        self.commandes: list[list[str]] = []
        self.synchronisations = 0
        self._reponses = reponses or (lambda _cmd: ResultatCommande(code_retour=0, sortie="1 passed"))

    def synchroniser(self) -> None:
        self.synchronisations += 1

    def executer(self, commande: list[str], delai: int = 120) -> ResultatCommande:
        self.commandes.append(commande)
        return self._reponses(commande)


def message_llm(contenu: str | None = None, appels: list[tuple[str, dict | str]] | None = None,
                jetons: tuple[int, int] = (100, 20), raisonnement: str | None = None) -> SimpleNamespace:
    """Construit une réponse au format du SDK openai.

    `raisonnement` reproduit le champ `reasoning` des modèles à raisonnement, qui renvoient leur
    réflexion à part et laissent `content` à None tant qu'ils n'ont pas produit de réponse finale.
    """
    tool_calls = None
    if appels:
        tool_calls = [
            SimpleNamespace(
                id=f"appel_{i}",
                function=SimpleNamespace(name=nom, arguments=args if isinstance(args, str) else json.dumps(args)),
            )
            for i, (nom, args) in enumerate(appels)
        ]
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=contenu, tool_calls=tool_calls,
                                                         reasoning=raisonnement))],
        usage=SimpleNamespace(prompt_tokens=jetons[0], completion_tokens=jetons[1], cost=0.001),
    )


class FauxOpenAI:
    """Client openai simulé : renvoie (ou lève) les éléments du scénario dans l'ordre."""

    def __init__(self, scenario: list):
        self.scenario = list(scenario)
        self.requetes: list[dict] = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **requete):
        self.requetes.append(requete)
        element = self.scenario.pop(0)
        if isinstance(element, Exception):
            raise element
        return element
