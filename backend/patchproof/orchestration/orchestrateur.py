"""Orchestrateur déterministe (M5, E-5.3) : enchaîne les failles une par une.

Pour chaque alerte : Attaquant -> (si confirmée) Défenseur -> validation, avec les limites
(3 tentatives, 30 appels d'outils, budget de jetons) et la reprise sans refaire les failles
déjà traitées. Ce n'est pas un agent : c'est un programme, prévisible et traçable.
"""

import logging

from sqlalchemy.orm import Session

from patchproof.agents.attaquant.agent import analyser_alerte, preuve_valide
from patchproof.agents.boucle import ArretAgent, BudgetEpuise, ContexteAgent
from patchproof.agents.defenseur.agent import proposer_correctif
from patchproof.core.git import revenir_a
from patchproof.core.git import valider as git_valider
from patchproof.core.interfaces import Bac
from patchproof.core.modeles import (
    Analyse,
    Correctif,
    EtatFaille,
    Faille,
    ParametresAdmin,
    TestPreuve,
)
from patchproof.core.schemas import Alerte
from patchproof.llm.client import ClientLLM, QuotaDepasse
from patchproof.suivi.publication import publier_etape, publier_etat_faille
from patchproof.validation.valideur import empreinte_tests, valider_correctif

journal = logging.getLogger("patchproof.orchestration")


class AnalyseEnPause(Exception):
    """Interruption propre (quota, budget) : l'analyse pourra être reprise."""


def _alerte_depuis_faille(faille: Faille) -> Alerte:
    return Alerte(
        outils=faille.outils.split(","), regle=faille.regle, fichier=faille.fichier, ligne=faille.ligne,
        cwe=faille.cwe, famille=faille.famille, gravite=faille.gravite, extrait=faille.extrait,
        exposee=faille.exposee, priorite=faille.priorite,
    )


def traiter_failles(s: Session, analyse: Analyse, bac: Bac, commande_test: str) -> None:
    """Traite toutes les failles non terminées et non exclues (reprise naturelle)."""
    params = s.get(ParametresAdmin, 1)
    base_sha = git_valider(bac.racine, "Base avant agents")

    a_traiter = [
        f for f in sorted(analyse.failles, key=lambda f: f.priorite)
        if not f.exclue and f.etat not in {EtatFaille.faux_positif, EtatFaille.corrigee, EtatFaille.revue_humaine}
    ]
    for faille in a_traiter:
        revenir_a(bac.racine, base_sha)  # chaque faille repart d'un code propre
        try:
            _traiter_une(s, analyse, faille, bac, params, commande_test)
        except (BudgetEpuise, QuotaDepasse) as e:
            raise AnalyseEnPause(str(e)) from e
        s.commit()


def _contexte(analyse: Analyse, faille: Faille, bac: Bac, params: ParametresAdmin) -> ContexteAgent:
    def consommer(entree: int, sortie: int, cout: float) -> None:
        analyse.jetons_utilises += entree + sortie
        analyse.cout_estime_usd += cout

    return ContexteAgent(
        analyse_id=analyse.id, faille_id=faille.id, bac=bac, client=ClientLLM(),
        publier=publier_etape,
        modele_attaquant=params.modele_attaquant, modele_defenseur=params.modele_defenseur,
        modele_leger=params.modele_leger,
        max_appels_outils=params.max_appels_outils_faille,
        budget_restant=lambda: params.budget_jetons_analyse - analyse.jetons_utilises,
        consommer=consommer,
    )


def _changer_etat(s: Session, analyse: Analyse, faille: Faille, etat: EtatFaille) -> None:
    faille.etat = etat
    s.flush()
    publier_etat_faille(analyse.id, faille.id, etat)


def _traiter_une(s, analyse, faille, bac, params, commande_test) -> None:
    alerte = _alerte_depuis_faille(faille)
    contexte = _contexte(analyse, faille, bac, params)
    _changer_etat(s, analyse, faille, EtatFaille.en_cours)

    # --- Phase Attaquant ---
    try:
        verdict = analyser_alerte(alerte, contexte)
    except ArretAgent as e:
        if isinstance(e, BudgetEpuise):
            raise
        return _changer_etat(s, analyse, faille, EtatFaille.revue_humaine)

    faille.tentatives_attaque += 1
    faille.point_entree = verdict.point_entree
    faille.justification = verdict.justification

    if not preuve_valide(verdict, contexte):
        return _changer_etat(s, analyse, faille, EtatFaille.faux_positif)

    test_fichier = verdict.test_fichier
    test_contenu = (bac.racine / test_fichier).read_text(encoding="utf-8", errors="replace")
    faille.test_preuve = TestPreuve(chemin=test_fichier, contenu=test_contenu)
    _changer_etat(s, analyse, faille, EtatFaille.confirmee)

    # Le test de preuve fait désormais partie du code de base de cette faille.
    sha_avec_test = git_valider(bac.racine, f"Test de preuve {test_fichier}")
    empreinte = empreinte_tests(bac.racine)

    # --- Phase Défenseur + validation (jusqu'à 3 tentatives) ---
    echec = None
    for tentative in range(1, params.max_tentatives_agent + 1):
        revenir_a(bac.racine, sha_avec_test)
        try:
            proposition, diff = proposer_correctif(alerte, test_fichier, test_contenu, contexte, echec)
        except ArretAgent as e:
            if isinstance(e, BudgetEpuise):
                raise
            break

        faille.tentatives_defense = tentative
        resultat = valider_correctif(bac, alerte, test_fichier, diff, empreinte, commande_test)
        correctif = Correctif(
            faille_id=faille.id, tentative=tentative, diff=diff, explication=proposition.explication,
            valide=resultat.accepte, resultat_validation=resultat.model_dump(),
        )
        s.add(correctif)
        contexte.etape("orchestrateur", "validation", resultat.message, succes=resultat.accepte)

        if resultat.accepte:
            return _changer_etat(s, analyse, faille, EtatFaille.corrigee)
        echec = resultat.message

    _changer_etat(s, analyse, faille, EtatFaille.revue_humaine)
