import httpx
import openai
import pytest

from patchproof.llm.client import CleAbsente, ClientLLM, LLMIndisponible, QuotaDepasse
from patchproof.llm.masquage import Masqueur
from tests.factices import FauxOpenAI, message_llm

_REQUETE = httpx.Request("POST", "https://openrouter.ai/api/v1/chat/completions")


def erreur_statut(classe, statut: int):
    return classe("erreur simulée", response=httpx.Response(statut, request=_REQUETE), body=None)


def client(scenario, attentes: list | None = None, masqueur: Masqueur | None = None) -> ClientLLM:
    enregistrer = attentes.append if attentes is not None else (lambda _s: None)
    return ClientLLM(masqueur=masqueur, client=FauxOpenAI(scenario), attendre=enregistrer)


MESSAGES = [{"role": "user", "content": "bonjour"}]


def test_cle_absente(monkeypatch):
    monkeypatch.setattr("patchproof.llm.client.parametres", lambda: _Params(""))
    with pytest.raises(CleAbsente):
        ClientLLM().discuter(MESSAGES, modele="m")


class _Params:
    def __init__(self, cle):
        self.openrouter_api_key = cle
        self.openrouter_base_url = "https://openrouter.ai/api/v1"
        self.delai_appel_llm = 60.0
        self.attentes_nouvelles_tentatives = (1.0, 4.0, 16.0)


def test_cle_refusee():
    with pytest.raises(CleAbsente):
        client([erreur_statut(openai.AuthenticationError, 401)]).discuter(MESSAGES, modele="m")


def test_quota_apres_trois_nouvelles_tentatives():
    attentes: list[float] = []
    erreurs = [erreur_statut(openai.RateLimitError, 429) for _ in range(4)]
    with pytest.raises(QuotaDepasse):
        client(erreurs, attentes).discuter(MESSAGES, modele="m")
    assert attentes == [1.0, 4.0, 16.0]


def test_credit_epuise_sans_nouvelle_tentative():
    attentes: list[float] = []
    with pytest.raises(QuotaDepasse):
        client([erreur_statut(openai.APIStatusError, 402)], attentes).discuter(MESSAGES, modele="m")
    assert attentes == []


def test_delai_depasse_puis_succes():
    attentes: list[float] = []
    scenario = [openai.APITimeoutError(request=_REQUETE), message_llm("ok")]
    reponse = client(scenario, attentes).discuter(MESSAGES, modele="m")
    assert reponse.contenu == "ok" and attentes == [1.0]


def test_indisponible_apres_quatre_echecs():
    scenario = [erreur_statut(openai.InternalServerError, 503) for _ in range(4)]
    with pytest.raises(LLMIndisponible):
        client(scenario).discuter(MESSAGES, modele="m")


def test_masquage_a_l_envoi_et_demasquage_a_la_reception():
    faux = FauxOpenAI([message_llm(None, [("lire_fichier", '{"chemin": "config.py", "note": "<SECRET_1>"}')])])
    llm = ClientLLM(client=faux, attendre=lambda _s: None)
    reponse = llm.discuter([{"role": "user", "content": 'DB_PASSWORD = "tres-secret-42"'}], modele="m")

    envoye = faux.requetes[0]["messages"][0]["content"]
    assert "tres-secret-42" not in envoye and "<SECRET_1>" in envoye
    assert reponse.appels_outils[0].arguments == {"chemin": "config.py", "note": "tres-secret-42"}
    assert reponse.jetons_entree == 100 and reponse.cout_usd == 0.001


def test_arguments_illisibles_signales():
    reponse = client([message_llm(None, [("lire_fichier", "{pas du json")])]).discuter(MESSAGES, modele="m")
    assert reponse.appels_outils[0].erreur.startswith("Arguments JSON invalides")


def test_le_raisonnement_est_lu_separement_du_contenu():
    """Un modèle à raisonnement renvoie sa réflexion à part et laisse content à None."""
    reponse = client([message_llm(None, raisonnement="Je regarde d'abord la route.")]).discuter(MESSAGES,
                                                                                               modele="m")
    assert reponse.contenu is None
    assert reponse.raisonnement == "Je regarde d'abord la route."


def test_le_raisonnement_est_demasque_a_la_reception():
    masqueur = Masqueur()
    assert "<SECRET_1>" in masqueur.masquer('DB_PASSWORD = "tres-secret-42"')
    scenario = [message_llm(None, raisonnement="la valeur envoyée est <SECRET_1>")]
    llm = ClientLLM(masqueur=masqueur, client=FauxOpenAI(scenario), attendre=lambda _s: None)
    assert llm.discuter(MESSAGES, modele="m").raisonnement == "la valeur envoyée est tres-secret-42"


def test_raisonnement_absent():
    assert client([message_llm("ok")]).discuter(MESSAGES, modele="m").raisonnement is None
