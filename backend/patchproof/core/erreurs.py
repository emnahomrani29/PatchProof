"""Erreurs métier converties en réponses HTTP {"detail", "code"} (voir docs/api.md)."""


class ErreurApi(Exception):
    statut = 400
    code = "requete_invalide"

    def __init__(self, detail: str, code: str | None = None, statut: int | None = None):
        super().__init__(detail)
        self.detail = detail
        if code:
            self.code = code
        if statut:
            self.statut = statut


class NonAuthentifie(ErreurApi):
    statut = 401
    code = "non_authentifie"


class Interdit(ErreurApi):
    statut = 403
    code = "interdit"


class Introuvable(ErreurApi):
    statut = 404
    code = "introuvable"


class Conflit(ErreurApi):
    statut = 409
    code = "conflit"


class Invalide(ErreurApi):
    statut = 422
    code = "invalide"
