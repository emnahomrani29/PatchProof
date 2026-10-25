"""Correspondance des règles Bandit / Semgrep vers les 4 familles du périmètre (E-2.2).

Ajouter une famille (exigence de maintenabilité) = ajouter une entrée ici et un exemple few-shot,
sans modifier les agents.
"""

from patchproof.core.modeles import Famille

# CWE associés à chaque famille retenue en v1.
# 259 est le code que Bandit attribue aux secrets codés en dur (B105-B107), en plus de 798.
CWE_FAMILLE: dict[str, Famille] = {
    "89": Famille.sqli,
    "78": Famille.commande,
    "798": Famille.secret,
    "259": Famille.secret,
    "22": Famille.traversee,
}

# Identifiants de test Bandit (B...) rattachés à une famille.
BANDIT_FAMILLE: dict[str, Famille] = {
    "B608": Famille.sqli,         # hardcoded_sql_expressions
    "B602": Famille.commande,     # subprocess_popen_with_shell_equals_true
    "B605": Famille.commande,     # start_process_with_a_shell
    "B105": Famille.secret,       # hardcoded_password_string
    "B106": Famille.secret,       # hardcoded_password_funcarg
    "B107": Famille.secret,       # hardcoded_password_default
}

# Bandit range plusieurs contrôles parmi les « notes d'audit » : ils ne constatent pas une
# vulnérabilité, ils invitent à relire le code. B404 (import de subprocess), B603 (subprocess
# sans shell) et B607 (chemin partiel) portent le CWE-78. Les rattacher à la famille « injection
# de commandes » a deux conséquences fâcheuses : chaque appel à subprocess devient une alerte, et
# un correctif qui remplace shell=True par une liste d'arguments en fait réapparaître une au même
# endroit, ce qui ferait échouer la 3e condition de validation (« l'alerte a disparu »).
REGLES_BANDIT_AUDIT = frozenset({"B404", "B603", "B607"})

# Règles Semgrep, identifiées par le dernier segment de leur identifiant (check_id).
# Nécessaire quand les métadonnées CWE du paquet du registre sont imprécises : par exemple
# `tainted-sql-string` annonce CWE-704 (conversion de type) alors que la règle décrit
# une injection SQL.
SEMGREP_FAMILLE: dict[str, Famille] = {
    "tainted-sql-string": Famille.sqli,
    "sql-injection-db-cursor-execute": Famille.sqli,
    "sql-injection-using-raw": Famille.sqli,
    "sql-injection-using-rawsql": Famille.sqli,
    "sql-injection-using-extra-where": Famille.sqli,
    "sqlalchemy-sql-injection": Famille.sqli,
    "pyramid-sqlalchemy-sql-injection": Famille.sqli,
    "subprocess-injection": Famille.commande,
    "dangerous-subprocess-use": Famille.commande,
    "dangerous-subprocess-use-tainted-env-args": Famille.commande,
    "subprocess-shell-true": Famille.commande,
    "dangerous-asyncio-shell": Famille.commande,
    "dangerous-asyncio-shell-tainted-env-args": Famille.commande,
    "hardcoded-token": Famille.secret,
    "jwt-python-hardcoded-secret": Famille.secret,
    "path-traversal-open": Famille.traversee,
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


def est_regle_audit(test_id: str | None) -> bool:
    """Vrai si la règle Bandit n'est qu'une note d'audit (voir REGLES_BANDIT_AUDIT)."""
    return bool(test_id) and test_id.upper() in REGLES_BANDIT_AUDIT


def famille_depuis_bandit(test_id: str | None) -> Famille | None:
    """Famille d'une règle Bandit : None si la règle est inconnue ou n'est qu'une note d'audit."""
    if est_regle_audit(test_id):
        return None
    return BANDIT_FAMILLE.get((test_id or "").upper())


def famille_bandit(test_id: str | None, cwe: str | None) -> Famille | None:
    """Famille d'une alerte Bandit : la règle fait foi, le CWE sert de secours."""
    if est_regle_audit(test_id):
        return None
    return BANDIT_FAMILLE.get((test_id or "").upper()) or famille_depuis_cwe(cwe)


def famille_semgrep(regle: str | None, cwe: str | None) -> Famille | None:
    """Famille d'une alerte Semgrep : le nom de la règle fait foi, le CWE sert de secours."""
    return SEMGREP_FAMILLE.get(regle or "") or famille_depuis_cwe(cwe)
