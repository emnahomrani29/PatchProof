"""Agent Defenseur (M4) : corrige une faille prouvee sans regression (docs/agents.md S4).

Le diff de reference n'est pas celui que l'agent declare : il est relu dans la copie de travail
(git diff depuis l'etat de depart), donc le correctif enregistre est exactement celui qui a ete teste.

Responsable : Emna Homrani (M4 - Agent Defenseur).
"""

from patchproof.agents.boucle import ContexteAgent, executer_agent
from patchproof.agents.outils import OUTILS_DEFENSEUR
from patchproof.agents.prompts import exemple_few_shot, prompt_defenseur
from patchproof.core.git import diff_depuis
from patchproof.core.schemas import Alerte, PropositionCorrectif


def _message_tache(alerte: Alerte, test_fichier: str, test_contenu: str,
                   exemple: str, echec_precedent: str | None) -> str:
    bloc_exemple = f"\n# Exemple de correctif pour cette famille\n{exemple}\n" if exemple else ""
    bloc_echec = (
        f"\n# Echec de ta tentative precedente (corrige-le)\n{echec_precedent}\n" if echec_precedent else ""
    )
    return (
        f"# Faille confirmee a corriger\n"
        f"fichier : {alerte.fichier}\n"
        f"ligne : {alerte.ligne}\n"
        f"famille : {alerte.famille.value if alerte.famille else 'inconnue'} ({alerte.cwe})\n\n"
        f"# Test de preuve (ne pas modifier)\n{test_fichier} :\n{test_contenu}\n"
        f"{bloc_exemple}{bloc_echec}\n"
        f"Produis un correctif minimal avec l'outil `remplacer` (de preference) ou `appliquer_diff`,"
        f" puis reponds en JSON."
    )


def proposer_correctif(
    alerte: Alerte,
    test_fichier: str,
    test_contenu: str,
    contexte: ContexteAgent,
    echec_precedent: str | None = None,
) -> tuple[PropositionCorrectif, str]:
    """Renvoie (proposition JSON, diff reellement applique dans la copie de travail)."""
    exemple = exemple_few_shot(alerte.famille, "correctif") if alerte.famille else ""
    proposition = executer_agent(
        "defenseur",
        prompt_defenseur(),
        _message_tache(alerte, test_fichier, test_contenu, exemple, echec_precedent),
        OUTILS_DEFENSEUR,
        PropositionCorrectif,
        contexte.modele_defenseur,
        contexte,
    )
    diff_reel = diff_depuis(contexte.bac.racine, "HEAD")
    contexte.etape("defenseur", "verdict", "Correctif propose", resultat=proposition.explication)
    return proposition, diff_reel