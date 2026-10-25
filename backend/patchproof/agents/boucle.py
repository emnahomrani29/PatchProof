"""Boucle générique d'un agent à appel d'outils (docs/agents.md §1).

appel LLM -> appel(s) d'outil -> résultats renvoyés au LLM -> … -> réponse finale JSON validée.
Les deux agents utilisent cette boucle et ne diffèrent que par le prompt, les outils et le schéma de sortie.
"""

from collections.abc import Callable
from dataclasses import dataclass, field

from pydantic import BaseModel, ValidationError

from patchproof.agents.outils import OUTILS, OutilRefuse, tronquer
from patchproof.core.interfaces import Bac
from patchproof.core.schemas import Etape, NomAgent
from patchproof.llm.client import ClientLLM, extraire_json

MAX_CORRECTIONS_JSON = 2
TAILLE_RESUME = 300


class ArretAgent(Exception):
    """L'agent s'arrête sans réponse exploitable ; l'orchestrateur décide de la suite."""

    code = "arret"


class LimiteAppelsAtteinte(ArretAgent):
    code = "limite_appels"


class BudgetEpuise(ArretAgent):
    code = "budget_epuise"


class SortieInvalide(ArretAgent):
    code = "sortie_invalide"


def _ignorer(*_args) -> None:
    return None


@dataclass
class ContexteAgent:
    """Ce dont un agent a besoin pour traiter une faille. Créé par l'orchestrateur (une instance par faille)."""

    analyse_id: int
    faille_id: int | None
    bac: Bac
    client: ClientLLM
    publier: Callable[[Etape], None] = _ignorer
    modele_attaquant: str = "anthropic/claude-sonnet-5.5"
    modele_defenseur: str = "anthropic/claude-sonnet-5.5"
    modele_leger: str = "anthropic/claude-haiku-5.5"
    max_appels_outils: int = 30
    budget_restant: Callable[[], int] = field(default=lambda: 10**12)
    consommer: Callable[[int, int, float], None] = _ignorer  # jetons entrée, sortie, coût
    appels_outils: int = 0  # partagé par l'Attaquant et le Défenseur sur une même faille

    def etape(self, agent: NomAgent, nature: str, resume: str, **autres) -> None:
        self.publier(Etape(analyse_id=self.analyse_id, faille_id=self.faille_id, agent=agent,
                           nature=nature, resume=resume[:2000], **autres))


def resumer_appel(nom: str, arguments: dict) -> str:
    courts = ", ".join(
        f"{k}={(v if len(str(v)) < 60 else str(v)[:57] + '…')!r}"
        for k, v in arguments.items() if k not in {"contenu", "diff"}
    )
    return f"{nom}({courts})"


def executer_agent[T: BaseModel](
    agent: NomAgent,
    prompt_systeme: str,
    objectif: str,
    noms_outils: list[str],
    schema: type[T],
    modele: str,
    contexte: ContexteAgent,
) -> T:
    outils = {nom: OUTILS[nom] for nom in noms_outils}
    definitions = [o.definition() for o in outils.values()]
    messages: list[dict] = [
        {"role": "system", "content": prompt_systeme},
        {"role": "user", "content": objectif},
    ]
    corrections = 0

    while True:
        if contexte.budget_restant() <= 0:
            raise BudgetEpuise("Budget de jetons de l'analyse épuisé.")

        reponse = contexte.client.discuter(messages, modele=modele, outils=definitions)
        contexte.consommer(reponse.jetons_entree, reponse.jetons_sortie, reponse.cout_usd)
        messages.append(reponse.message_brut)

        if reponse.contenu and reponse.contenu.strip():
            contexte.etape(agent, "raisonnement", tronquer(reponse.contenu.strip(), TAILLE_RESUME),
                           jetons_entree=reponse.jetons_entree, jetons_sortie=reponse.jetons_sortie)

        if reponse.appels_outils:
            for appel in reponse.appels_outils:
                messages.append({"role": "tool", "tool_call_id": appel.id,
                                 "content": _executer_outil(agent, appel, outils, contexte)})
            continue

        try:
            return extraire_json(reponse.contenu, schema)
        except (ValidationError, ValueError) as e:
            corrections += 1
            contexte.etape(agent, "erreur", f"Réponse finale invalide ({corrections}/{MAX_CORRECTIONS_JSON})",
                           resultat=tronquer(str(e), 1000), succes=False)
            if corrections > MAX_CORRECTIONS_JSON:
                raise SortieInvalide("L'agent n'a pas fourni de réponse JSON valide.") from e
            messages.append({
                "role": "user",
                "content": "Ta réponse finale ne respecte pas le format attendu :\n"
                           f"{tronquer(str(e), 1500)}\n"
                           "Réponds uniquement avec l'objet JSON demandé, ou appelle un outil.",
            })


def _executer_outil(agent: NomAgent, appel, outils: dict, contexte: ContexteAgent) -> str:
    if contexte.appels_outils >= contexte.max_appels_outils:
        raise LimiteAppelsAtteinte(f"Limite de {contexte.max_appels_outils} appels d'outils atteinte.")
    contexte.appels_outils += 1

    resume = resumer_appel(appel.nom, appel.arguments)
    contexte.etape(agent, "appel_outil", resume, outil=appel.nom,
                   arguments={k: tronquer(str(v), 2000) for k, v in appel.arguments.items()})

    succes = False
    if appel.erreur:
        resultat = appel.erreur
    elif appel.nom not in outils:
        resultat = f"Outil non autorisé pour l'agent {agent} : {appel.nom}. Outils disponibles : {', '.join(outils)}."
    else:
        outil = outils[appel.nom]
        try:
            parametres = outil.parametres.model_validate(appel.arguments)
            resultat = outil.fonction(contexte.bac, parametres)
            succes = True
        except ValidationError as e:
            resultat = f"Paramètres invalides : {tronquer(str(e), 1000)}"
        except OutilRefuse as e:
            resultat = str(e)

    contexte.etape(agent, "resultat_outil", tronquer(resultat, TAILLE_RESUME), outil=appel.nom,
                   resultat=tronquer(resultat), succes=succes)
    return resultat
