"""Client LLM unique (OpenRouter, API compatible OpenAI) avec les garde-fous du module.

- masquage de tout le texte envoyé, démasquage de tout le texte reçu ;
- délai de 60 s par appel, 3 nouvelles tentatives espacées (1 s, 4 s, 16 s) ;
- erreurs typées : clé absente, quota dépassé, service indisponible ;
- comptage des jetons et du coût.
"""

import json
import re
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import openai
from pydantic import BaseModel, ValidationError

from patchproof.core.config import parametres
from patchproof.llm.masquage import Masqueur


class ErreurLLM(Exception):
    code = "llm_erreur"

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class CleAbsente(ErreurLLM):
    code = "llm_cle_absente"


class QuotaDepasse(ErreurLLM):
    code = "llm_quota_depasse"


class LLMIndisponible(ErreurLLM):
    code = "llm_indisponible"


@dataclass
class AppelOutil:
    id: str
    nom: str
    arguments: dict[str, Any]
    erreur: str | None = None  # arguments illisibles (JSON invalide)


@dataclass
class ReponseLLM:
    contenu: str | None
    raisonnement: str | None = None  # réflexion du modèle, séparée de la réponse finale
    appels_outils: list[AppelOutil] = field(default_factory=list)
    jetons_entree: int = 0
    jetons_sortie: int = 0
    cout_usd: float = 0.0
    message_brut: dict[str, Any] = field(default_factory=dict)  # à rajouter tel quel à l'historique


class ClientLLM:
    def __init__(
        self,
        masqueur: Masqueur | None = None,
        client: Any = None,
        attendre: Callable[[float], None] = time.sleep,
    ):
        p = parametres()
        self.masqueur = masqueur or Masqueur()
        self._attendre = attendre
        self._attentes = p.attentes_nouvelles_tentatives
        if client is not None:
            self._client = client
        elif p.openrouter_api_key:
            self._client = openai.OpenAI(
                api_key=p.openrouter_api_key,
                base_url=p.openrouter_base_url,
                timeout=p.delai_appel_llm,
                max_retries=0,
            )
        else:
            self._client = None

    # -- envoi -------------------------------------------------------------------

    def _masquer_message(self, message: dict[str, Any]) -> dict[str, Any]:
        copie = dict(message)
        if isinstance(copie.get("content"), str):
            copie["content"] = self.masqueur.masquer(copie["content"])
        if copie.get("tool_calls"):
            copie["tool_calls"] = [
                {**tc, "function": {**tc["function"],
                                    "arguments": self.masqueur.masquer(tc["function"]["arguments"])}}
                for tc in copie["tool_calls"]
            ]
        return copie

    def discuter(
        self,
        messages: list[dict[str, Any]],
        modele: str,
        outils: list[dict[str, Any]] | None = None,
    ) -> ReponseLLM:
        if self._client is None:
            raise CleAbsente("Aucune clé OpenRouter configurée (OPENROUTER_API_KEY dans .env).")

        requete: dict[str, Any] = {
            "model": modele,
            "messages": [self._masquer_message(m) for m in messages],
            "extra_body": {"usage": {"include": True}},
        }
        if outils:
            requete["tools"] = outils

        derniere_erreur: Exception | None = None
        for tentative in range(len(self._attentes) + 1):
            if tentative:
                self._attendre(self._attentes[tentative - 1])
            try:
                reponse = self._client.chat.completions.create(**requete)
                return self._lire(reponse)
            except openai.AuthenticationError as e:
                raise CleAbsente("Clé OpenRouter refusée : vérifiez OPENROUTER_API_KEY.") from e
            except openai.APIStatusError as e:
                if e.status_code == 402:
                    raise QuotaDepasse("Crédit OpenRouter épuisé : l'analyse est mise en pause.") from e
                if e.status_code == 429 or e.status_code >= 500:
                    derniere_erreur = e
                    continue
                raise ErreurLLM(f"Requête refusée par le LLM ({e.status_code}) : {e.message}") from e
            except (openai.APITimeoutError, openai.APIConnectionError) as e:
                derniere_erreur = e
                continue

        if isinstance(derniere_erreur, openai.RateLimitError):
            raise QuotaDepasse("Quota OpenRouter dépassé après 3 nouvelles tentatives : analyse en pause.")
        raise LLMIndisponible(
            f"Le LLM ne répond pas après 3 nouvelles tentatives ({type(derniere_erreur).__name__})."
        )

    # -- réception ---------------------------------------------------------------

    def texte_raisonnement(self, message: Any) -> str | None:
        """Réflexion d'un modèle « raisonneur », ou None.

        Ces modèles renvoient leur réflexion dans un champ distinct (`reasoning`, ou
        `reasoning_details[].text` chez OpenRouter) et laissent `content` à `null` tant qu'ils n'ont
        pas produit de réponse finale. Sans cette lecture, un tour qui ne contient que du
        raisonnement passe pour une réponse vide et son texte est perdu.
        """
        morceaux: list[str] = []
        direct = getattr(message, "reasoning", None)
        if direct:
            morceaux.append(direct)
        for bloc in getattr(message, "reasoning_details", None) or []:
            texte = bloc.get("text") if isinstance(bloc, dict) else getattr(bloc, "text", None)
            if texte and texte not in morceaux:
                morceaux.append(texte)
        texte = "\n".join(m.strip() for m in morceaux if m).strip()
        if not texte:
            return None
        return self.masqueur.demasquer(texte) or None

    def _lire(self, reponse: Any) -> ReponseLLM:
        if not getattr(reponse, "choices", None):
            raise LLMIndisponible("Réponse vide du LLM.")
        message = reponse.choices[0].message
        contenu = self.masqueur.demasquer(message.content) if message.content else None
        raisonnement = self.texte_raisonnement(message)

        appels: list[AppelOutil] = []
        appels_bruts: list[dict[str, Any]] = []
        for tc in message.tool_calls or []:
            texte_args = self.masqueur.demasquer(tc.function.arguments or "{}")
            try:
                args = json.loads(texte_args)
                erreur = None if isinstance(args, dict) else "Les arguments doivent être un objet JSON."
                args = args if isinstance(args, dict) else {}
            except json.JSONDecodeError as e:
                args, erreur = {}, f"Arguments JSON invalides : {e.msg}"
            appels.append(AppelOutil(id=tc.id, nom=tc.function.name, arguments=args, erreur=erreur))
            appels_bruts.append({
                "id": tc.id,
                "type": "function",
                "function": {"name": tc.function.name, "arguments": texte_args},
            })

        brut: dict[str, Any] = {"role": "assistant", "content": contenu}
        if appels_bruts:
            brut["tool_calls"] = appels_bruts

        usage = getattr(reponse, "usage", None)
        return ReponseLLM(
            contenu=contenu,
            raisonnement=raisonnement,
            appels_outils=appels,
            jetons_entree=getattr(usage, "prompt_tokens", 0) or 0,
            jetons_sortie=getattr(usage, "completion_tokens", 0) or 0,
            cout_usd=float(getattr(usage, "cost", 0) or 0),
            message_brut=brut,
        )


_BLOC_JSON = re.compile(r"```(?:json)?\s*(\{[\s\S]*\})\s*```")


def extraire_json[T: BaseModel](texte: str | None, schema: type[T]) -> T:
    """Valide la réponse finale d'un agent. Lève ValidationError ou ValueError si elle est invalide."""
    if not texte:
        raise ValueError("Réponse finale vide : un objet JSON est attendu.")
    bloc = _BLOC_JSON.search(texte)
    candidat = bloc.group(1) if bloc else texte[texte.find("{"): texte.rfind("}") + 1]
    if not candidat:
        raise ValueError("Aucun objet JSON trouvé dans la réponse.")
    return schema.model_validate_json(candidat)


__all__ = [
    "AppelOutil",
    "CleAbsente",
    "ClientLLM",
    "ErreurLLM",
    "LLMIndisponible",
    "QuotaDepasse",
    "ReponseLLM",
    "ValidationError",
    "extraire_json",
]
