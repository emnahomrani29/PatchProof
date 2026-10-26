# Évolution des prompts

Une ligne par changement, la plus récente en haut. Cette page sert à la présentation des prompts en soutenance.

| Version | Prompt | Changement | Raison (problème observé) | Effet mesuré |
|---|---|---|---|---|
| v1 | `attaquant/systeme.md`, `defenseur/systeme.md` | Première version : rôle, méthode en étapes, interdits, sortie JSON imposée, et tableau « correctif qui fait disparaître l'alerte » par famille | Mise en service des deux agents | À mesurer sur `demo-app/` (voir [demo.md](../docs/demo.md) §3) |
| v1 | `exemples/cwe-89|78|798|22/{attaque,correctif}.md` | Un exemple few-shot par famille : démarche de preuve d'un côté, diff minimal de l'autre | Sans exemple, l'Attaquant écrit des tests qui ne prouvent rien et le Défenseur laisse l'alerte en place | À mesurer |

Notes de rédaction :

- Les prompts s'appuient sur la structure **Rôle / Contexte / Méthode / Interdits / Format** vue en séance 2.
- Chaque modification doit être un commit `feat(prompts): …` expliquant la raison du changement, puis une
  ligne ajoutée en haut de ce tableau avec l'effet mesuré sur `demo-app/`.

