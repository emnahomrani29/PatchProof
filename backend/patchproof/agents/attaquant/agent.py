"""Agent Attaquant (M3) : prouve ou réfute une alerte par un test (docs/agents.md §3).

Ce module assemble le contexte (alerte + exemple few-shot) et délègue le raisonnement à la
boucle d'agent générique. La preuve est toujours re-vérifiée par l'orchestrateur, jamais crue
sur parole.
"""

from patchproof.agents.boucle import ContexteAgent, executer_agent
from patchproof.agents.outils import OUTILS_ATTAQUANT, ParamsTests, executer_tests
from patchproof.agents.prompts import exemple_few_shot, prompt_attaquant
from patchproof.core.schemas import Alerte, VerdictAttaquant


def _message_tache(alerte: Alerte, exemple: str) -> str:
    bloc_exemple = f"\n\n# Exemple pour cette famille de faille\n{exemple}\n" if exemple else ""
    return (
        f"# Alerte à analyser\n"
        f"alerte_id : {alerte_id(alerte)}\n"
        f"famille : {alerte.famille.value if alerte.famille else 'inconnue'}\n"
        f"fichier : {alerte.fichier}\n"
        f"ligne : {alerte.ligne}\n"
        f"règle : {alerte.regle} ({alerte.cwe})\n"
        f"extrait signalé :\n{alerte.extrait}\n"
        f"{bloc_exemple}\n"
        f"Analyse cette alerte en suivant ta méthode, puis rends ton verdict en JSON."
    )


def alerte_id(alerte: Alerte) -> str:
    """Identifiant lisible d'une alerte (ex. B608-app.py-42)."""
    return f"{alerte.regle.split('.')[-1]}-{alerte.fichier.split('/')[-1]}-{alerte.ligne}"


def analyser_alerte(alerte: Alerte, contexte: ContexteAgent) -> VerdictAttaquant:
    exemple = exemple_few_shot(alerte.famille, "attaque") if alerte.famille else ""
    verdict = executer_agent(
        "attaquant",
        prompt_attaquant(),
        _message_tache(alerte, exemple),
        OUTILS_ATTAQUANT,
        VerdictAttaquant,
        contexte.modele_attaquant,
        contexte,
    )
    contexte.etape("attaquant", "verdict", f"Verdict : {verdict.verdict}", resultat=verdict.justification)
    return verdict


def preuve_valide(verdict: VerdictAttaquant, contexte: ContexteAgent) -> bool:
    """Re-vérifie qu'un verdict « confirmee » s'appuie sur un test qui passe réellement."""
    if verdict.verdict != "confirmee" or not verdict.test_fichier:
        return False
    if not (contexte.bac.racine / verdict.test_fichier).is_file():
        return False
    resultat = executer_tests(contexte.bac, ParamsTests(cible=verdict.test_fichier))
    return "Code retour pytest : 0" in resultat
