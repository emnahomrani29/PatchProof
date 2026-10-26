# Règles Semgrep locales

Règles propres au projet, ajoutées à celles du registre Semgrep (`/regles/*.yml` dans l'image Docker).
Responsable : **Abdel Kader Kaddachi (M2 – Détection)**.

## Fichiers de règles

- `regles_custom.yml` : Règles spécifiques au périmètre des 4 familles (CWE-89, CWE-78, CWE-798, CWE-22) venant en complément des règles standards du registre Semgrep.

## Ajouter une nouvelle règle

1. Déclarer la règle dans un fichier `.yml` dans ce dossier avec son motif (`pattern` ou `patterns`), son message et ses métadonnées (CWE).
2. Vérifier la correspondance dans `backend/patchproof/detection/familles.py` (`SEMGREP_FAMILLE` ou `CWE_FAMILLE`).
3. Ajouter un test unitaire dans `backend/tests/detection/test_familles.py`.
