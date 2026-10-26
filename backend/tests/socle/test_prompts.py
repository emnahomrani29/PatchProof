"""Vérifie les prompts versionnés présents dans ce lot (socle + Attaquant).

Les prompts du Défenseur et les exemples « correctif.md » sont livrés par le module M4.
"""

from patchproof.agents.prompts import DEFAUT_ATTAQUANT, exemple_few_shot, prompt_attaquant
from patchproof.core.modeles import Famille


def test_le_prompt_attaquant_vient_du_depot():
    """Un fichier manquant ferait silencieusement retomber l'Attaquant sur le prompt par défaut."""
    assert prompt_attaquant() != DEFAUT_ATTAQUANT


def test_le_prompt_attaquant_impose_le_format_de_sortie():
    texte = prompt_attaquant()
    assert "confirmee" in texte and "faux_positif" in texte
    assert "tests/security/" in texte


def test_un_exemple_attaque_par_famille_est_present():
    for famille in Famille:
        contenu = exemple_few_shot(famille, "attaque")
        assert contenu, f"exemple few-shot manquant : {famille.value}/attaque.md"
