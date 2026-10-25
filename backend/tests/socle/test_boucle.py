import json
from typing import Literal

import pytest
from pydantic import BaseModel

from patchproof.agents.boucle import (
    BudgetEpuise,
    ContexteAgent,
    LimiteAppelsAtteinte,
    SortieInvalide,
    executer_agent,
)
from patchproof.llm.client import ClientLLM
from tests.factices import FauxBac, FauxOpenAI, message_llm


class Sortie(BaseModel):
    verdict: Literal["oui", "non"]


def contexte(tmp_path, scenario, **options) -> tuple[ContexteAgent, list]:
    (tmp_path / "app.py").write_text("print('x')\n", encoding="utf-8")
    etapes: list = []
    ctx = ContexteAgent(
        analyse_id=1, faille_id=7, bac=FauxBac(tmp_path),
        client=ClientLLM(client=FauxOpenAI(scenario), attendre=lambda _s: None),
        publier=etapes.append, **options,
    )
    return ctx, etapes


def lancer(ctx, outils=("lire_fichier",)):
    return executer_agent("attaquant", "système", "objectif", list(outils), Sortie, "modele", ctx)


def test_appel_d_outil_puis_reponse_finale(tmp_path):
    ctx, etapes = contexte(tmp_path, [
        message_llm("Je lis le fichier.", [("lire_fichier", {"chemin": "app.py"})]),
        message_llm('```json\n{"verdict": "oui"}\n```'),
    ])
    assert lancer(ctx) == Sortie(verdict="oui")
    natures = [e.nature for e in etapes]
    assert natures == ["raisonnement", "appel_outil", "resultat_outil", "raisonnement"]
    assert etapes[2].succes and "print('x')" in etapes[2].resultat
    assert ctx.appels_outils == 1


def test_resultat_d_outil_renvoye_au_llm(tmp_path):
    faux = [message_llm(None, [("lire_fichier", {"chemin": "app.py"})]), message_llm('{"verdict": "non"}')]
    ctx, _ = contexte(tmp_path, faux)
    lancer(ctx)
    messages = ctx.client._client.requetes[1]["messages"]
    assert messages[-1]["role"] == "tool" and "print('x')" in messages[-1]["content"]


def test_outil_non_autorise(tmp_path):
    ctx, etapes = contexte(tmp_path, [
        message_llm(None, [("appliquer_diff", {"diff": "--- a/app.py\n+++ b/app.py\n"})]),
        message_llm('{"verdict": "non"}'),
    ])
    lancer(ctx)
    assert not etapes[1].succes and "non autorisé" in etapes[1].resultat


def test_parametres_invalides_renvoyes_a_l_agent(tmp_path):
    ctx, etapes = contexte(tmp_path, [
        message_llm(None, [("lire_fichier", {"debut": 3})]),
        message_llm('{"verdict": "non"}'),
    ])
    lancer(ctx)
    assert "Paramètres invalides" in etapes[1].resultat


def test_sortie_invalide_apres_deux_corrections(tmp_path):
    ctx, _ = contexte(tmp_path, [message_llm("pas de json"), message_llm('{"verdict": "peut-être"}'),
                                 message_llm("toujours pas")])
    with pytest.raises(SortieInvalide):
        lancer(ctx)


def test_correction_acceptee(tmp_path):
    ctx, _ = contexte(tmp_path, [message_llm("pas de json"), message_llm(json.dumps({"verdict": "oui"}))])
    assert lancer(ctx).verdict == "oui"


def test_limite_d_appels(tmp_path):
    appel = message_llm(None, [("lire_fichier", {"chemin": "app.py"})])
    ctx, _ = contexte(tmp_path, [appel] * 5, max_appels_outils=3)
    with pytest.raises(LimiteAppelsAtteinte):
        lancer(ctx)
    assert ctx.appels_outils == 3


def test_budget_epuise(tmp_path):
    ctx, _ = contexte(tmp_path, [], budget_restant=lambda: 0)
    with pytest.raises(BudgetEpuise):
        lancer(ctx)


def test_consommation_comptee(tmp_path):
    total = []
    ctx, _ = contexte(tmp_path, [message_llm('{"verdict": "oui"}', jetons=(1000, 50))],
                      consommer=lambda e, s, c: total.append((e, s, c)))
    lancer(ctx)
    assert total == [(1000, 50, 0.001)]
