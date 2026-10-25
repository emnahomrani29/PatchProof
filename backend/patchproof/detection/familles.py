"""Correspondance des règles Bandit / Semgrep vers les 4 familles du périmètre (E-2.2).

Ajouter une famille (exigence de maintenabilité) = ajouter une entrée ici et un exemple few-shot,
sans modifier les agents.
"""

from patchproof.core.modeles import Famille

# CWE associés à chaque famille retenue en v1.
CWE_FAMILLE: dict[str, Famille] = {
    "89": Famille.sqli,
    "78": Famille.commande,
    "798": Famille.secret,
    "22": Famille.traversee,
}

# Identifiants de test Bandit (B...) rattachés à une famille, quand le CWE n'est pas fourni.
BANDIT_FAMILLE: dict[str, Famille] = {
    "B608": Famille.sqli,         # hardcoded_sql_expressions
    "B602": Famille.commande,     # subprocess_popen_with_shell_equals_true
    "B603": Famille.commande,     # subprocess_without_shell_equals_true
    "B605": Famille.commande,     # start_process_with_a_shell
    "B607": Famille.commande,     # start_process_with_partial_path
    "B105": Famille.secret,       # hardcoded_password_string
    "B106": Famille.secret,       # hardcoded_password_funcarg
    "B107": Famille.secret,       # hardcoded_password_default
}

LIBELLE: dict[Famille, str] = {
    Famille.sqli: "Injection SQL (CWE-89)",
    Famille.commande: "Injection de commandes (CWE-78)",
    Famille.secret: "Secret codé en dur (CWE-798)",
    Famille.traversee: "Traversée de répertoire (CWE-22)",
}


def famille_depuis_cwe(cwe: str | None) -> Famille | None:
    if not cwe:
        return None
    numero = cwe.upper().replace("CWE-", "").strip()
    return CWE_FAMILLE.get(numero)


def famille_depuis_bandit(test_id: str) -> Famille | None:
    return BANDIT_FAMILLE.get(test_id.upper())
