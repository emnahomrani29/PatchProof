from patchproof.llm.masquage import Masqueur


def test_secret_affecte_est_masque_et_restaure():
    m = Masqueur()
    code = 'API_KEY = "a8f5f167f44f4964e6c998dee827110c"\nDB_PASSWORD = "hunter2-prod"\n'
    masque = m.masquer(code)
    assert "a8f5f167" not in masque and "hunter2" not in masque
    assert 'API_KEY = "<SECRET_1>"' in masque
    assert 'DB_PASSWORD = "<SECRET_2>"' in masque
    assert m.demasquer(masque) == code


def test_meme_valeur_meme_marqueur():
    m = Masqueur()
    premier = m.masquer('token = "abcdef123456"')
    second = m.masquer('headers = {"X-Token": "abcdef123456"}')
    assert "<SECRET_1>" in premier and "<SECRET_1>" in second
    assert "abcdef123456" not in second


def test_formats_de_cles_connus():
    m = Masqueur()
    texte = (
        "cle = sk-or-v1-0123456789abcdefghijklmnop\n"
        "gh = ghp_0123456789abcdefghijklmnopqrstuvwxyz\n"
        "aws = AKIAABCDEFGHIJKLMNOP\n"
    )
    masque = m.masquer(texte)
    for valeur in ("sk-or-v1", "ghp_0123", "AKIAABCD"):
        assert valeur not in masque


def test_donnees_personnelles():
    m = Masqueur()
    masque = m.masquer("Contact : amine.ben@exemple.tn, tél. +216 22 333 444")
    assert "amine.ben@exemple.tn" not in masque and "<EMAIL_1>" in masque
    assert "22 333 444" not in masque and "<TEL_1>" in masque


def test_code_ordinaire_inchange():
    m = Masqueur()
    code = (
        'SECRET_KEY = os.environ["SECRET_KEY"]\n'
        'password = request.form.get("password")\n'
        "for i in range(10):\n    total += i * 3600\n"
        'token = ""\n'
    )
    assert m.masquer(code) == code
    assert m.valeurs_masquees == set()
