# API

Base : `http://localhost:8000`. Documentation interactive générée par FastAPI : `/docs`.
Toutes les routes `/api/*` sauf l'inscription et la connexion demandent l'en-tête `Authorization: Bearer <jeton>`.

## Conventions

- JSON en entrée et en sortie, noms de champs en `snake_case` français.
- Erreurs : `{"detail": "message lisible", "code": "code_machine"}` avec le statut HTTP adapté.
- Rôles : `developpeur`, `responsable_securite`, `administrateur`. Un rôle supérieur hérite des droits du précédent.

| Code d'erreur | Statut | Cas |
|---|---|---|
| `non_authentifie` | 401 | Jeton absent ou expiré |
| `interdit` | 403 | Rôle insuffisant ou ressource d'un autre utilisateur |
| `introuvable` | 404 | Ressource inexistante |
| `projet_trop_gros` | 422 | Plus de 5 000 lignes Python |
| `framework_non_supporte` | 422 | Ni Flask ni FastAPI détecté |
| `llm_cle_absente` | 503 | `OPENROUTER_API_KEY` non configurée |
| `llm_quota_depasse` | 503 | Quota ou crédit OpenRouter épuisé, analyse mise en pause |

## M1 – Authentification

| Méthode | Route | Corps | Réponse |
|---|---|---|---|
| POST | `/api/auth/inscription` | `{email, nom, mot_de_passe}` | 201 `Utilisateur` |
| POST | `/api/auth/connexion` | `{email, mot_de_passe}` | `{jeton, utilisateur}` |
| POST | `/api/auth/deconnexion` | – | 204 (le client oublie le jeton) |
| GET | `/api/auth/moi` | – | `Utilisateur` (+ `github_connecte: bool`) |
| GET | `/api/auth/github` | – | `{url}` : page d'autorisation GitHub |
| GET | `/api/auth/github/retour?code=&state=` | – | Redirection vers l'interface |

## M1 – Projets

| Méthode | Route | Corps | Réponse |
|---|---|---|---|
| GET | `/api/projets` | – | `Projet[]` |
| POST | `/api/projets` | `{url_github}` | 201 `Projet` |
| POST | `/api/projets/zip` | multipart `fichier` | 201 `Projet` |
| GET | `/api/projets/{id}` | – | `Projet` + dernières analyses |
| DELETE | `/api/projets/{id}` | – | 204 |

`Projet` : `{id, nom, source, url_github, framework, commande_test, nb_lignes, cree_le}`.

## M1 – Administration (rôle `administrateur`)

| Méthode | Route | Corps | Réponse |
|---|---|---|---|
| GET | `/api/admin/utilisateurs` | – | `Utilisateur[]` |
| PATCH | `/api/admin/utilisateurs/{id}` | `{role?, actif?}` | `Utilisateur` |
| GET | `/api/admin/parametres` | – | `Parametres` |
| PUT | `/api/admin/parametres` | `Parametres` | `Parametres` |

`Parametres` : `{budget_jetons_analyse, max_tentatives_agent, max_appels_outils_faille, modele_attaquant, modele_defenseur, modele_leger}`.

## M2 / M5 – Analyses

| Méthode | Route | Corps | Réponse |
|---|---|---|---|
| POST | `/api/projets/{id}/analyses` | – | 202 `Analyse` (état `en_attente`) |
| GET | `/api/projets/{id}/analyses` | – | `Analyse[]` (historique) |
| GET | `/api/analyses/{id}` | – | `Analyse` + compteurs |
| GET | `/api/analyses/{id}/failles` | – | `Faille[]` triées par priorité |
| PATCH | `/api/failles/{id}` | `{exclue: bool}` | `Faille` (état `selection` uniquement) |
| POST | `/api/analyses/{id}/demarrer` | – | 202 : lance les agents sur les failles non exclues |
| POST | `/api/analyses/{id}/reprendre` | – | 202 : reprend une analyse `en_pause` |
| POST | `/api/analyses/{id}/relancer` | – | 202 : relance une analyse interrompue |
| GET | `/api/analyses/{id}/etapes?faille_id=` | – | `EtapeAgent[]` (historique du suivi) |

**Analyse interrompue.** Une tâche abandonnée — conteneur redémarré pendant l'analyse, coupure — laisse
l'analyse bloquée dans son dernier état (`preparation`, `detection` ou `traitement`) : sans point de
reprise, l'interface attend indéfiniment. `POST /api/analyses/{id}/relancer` remet en file la tâche de la
phase en cours. La préparation repart d'une liste d'alertes propre (aucun doublon) et le traitement ignore
les failles déjà terminées : relancer ne refait pas le travail déjà fait. Une analyse en `selection`
attend au contraire une décision du développeur : utiliser `…/demarrer`.

`Analyse` : `{id, projet_id, etat, cree_le, termine_le, jetons_utilises, cout_estime_usd, message_erreur, compteurs: {total, confirmees, faux_positifs, corrigees, revue_humaine}}`.

`Faille` : `{id, outil, regle, fichier, ligne, cwe, famille, gravite, exposee, extrait, exclue, etat, point_entree, justification}`.

## M4 / M6 – Correctifs, rapport, livraison

| Méthode | Route | Corps | Réponse |
|---|---|---|---|
| GET | `/api/failles/{id}/detail` | – | `Faille` + test de preuve + tentatives de correctif + résultats de validation |
| PATCH | `/api/correctifs/{id}` | `{decision: "accepte" \| "rejete"}` | `Correctif` |
| GET | `/api/analyses/{id}/rapport` | – | `Rapport` (JSON) |
| GET | `/api/analyses/{id}/rapport.pdf` | – | `application/pdf` |
| GET | `/api/analyses/{id}/patch` | – | `text/x-diff` : correctifs acceptés + tests de non-régression |
| POST | `/api/analyses/{id}/pull-request` | `{branche?, titre?}` | `{url}` |

## M6 – Revue humaine (rôle `responsable_securite`)

| Méthode | Route | Corps | Réponse |
|---|---|---|---|
| GET | `/api/revue` | – | `Faille[]` à l'état `revue_humaine`, tous projets |
| POST | `/api/failles/{id}/revue` | `{decision: "corrigee_manuellement" \| "faux_positif" \| "acceptee_risque", commentaire}` | `Faille` |

## WebSocket – suivi en direct

`ws://localhost:8000/ws/analyses/{id}?jeton=<jeton>`

À la connexion, le serveur envoie l'état courant, puis chaque nouvel événement (< 1 s après sa production).

```jsonc
// Étape d'un agent
{"type": "etape", "faille_id": 12, "agent": "attaquant", "nature": "appel_outil",
 "resume": "Lecture de app.py autour de la ligne 42", "outil": "lire_fichier",
 "succes": true, "horodatage": "…"}

// Changement d'état d'une faille
{"type": "etat_faille", "faille_id": 12, "etat": "confirmee"}

// Changement d'état de l'analyse
{"type": "etat_analyse", "etat": "en_pause", "message": "Quota OpenRouter dépassé", "compteurs": {…}}
```

`nature` ∈ `raisonnement`, `appel_outil`, `resultat_outil`, `verdict`, `validation`, `erreur`.
`agent` ∈ `attaquant`, `defenseur`, `orchestrateur`.
