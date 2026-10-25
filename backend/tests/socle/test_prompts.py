"""Vérifie que les prompts versionnés du dossier `prompts/` sont bien ceux utilisés par les agents."""

from patchproof.agents.prompts import (
    DEFAUT_ATTAQUANT,
    DEFAUT_DEFENSEUR,
    exemple_few_shot,
    prompt_attaquant,
    prompt_defenseur,
)
from patchproof.core.modeles import Famille


def test_les_prompts_systeme_viennent_du_depot():
    """Un fichier manquant ferait silencieusement retomber les agents sur le prompt par défaut."""
    assert prompt_attaquant() != DEFAUT_ATTAQUANT
    assert prompt_defenseur() != DEFAUT_DEFENSEUR


def test_le_prompt_attaquant_impose_le_format_de_sortie():
    texte = prompt_attaquant()
    assert "confirmee" in texte and "faux_positif" in texte
    assert "tests/security/" in texte


def test_le_prompt_defenseur_rappelle_les_interdits_et_les_conditions():
    texte = prompt_defenseur()
    assert "tests/" in texte          # interdiction de toucher aux tests
    assert "alerte" in texte          # 3e condition : l'alerte doit disparaître
    assert "diff" in texte            # format attendu : diff unifié


def test_les_huit_exemples_few_shot_sont_presents():
    for famille in Famille:
        for role in ("attaque", "correctif"):
            contenu = exemple_few_shot(famille, role)
            assert contenu, f"exemple few-shot manquant : {famille.value}/{role}.md"
