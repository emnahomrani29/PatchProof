// Types des réponses de l'API (docs/api.md). Miroir de backend/patchproof/core/schemas.py.

export type Role = 'developpeur' | 'responsable_securite' | 'administrateur'

export interface Utilisateur {
  id: number
  email: string
  nom: string
  role: Role
  actif: boolean
  github_login: string | null
}

export interface Projet {
  id: number
  nom: string
  source: 'github' | 'zip'
  url_github: string | null
  framework: 'flask' | 'fastapi' | null
  commande_test: string | null
  nb_lignes: number
  cree_le: string
}

export type EtatAnalyse =
  | 'en_attente'
  | 'preparation'
  | 'detection'
  | 'selection'
  | 'traitement'
  | 'en_pause'
  | 'terminee'
  | 'echec'

export interface Compteurs {
  total: number
  exclues: number
  en_attente: number
  confirmees: number
  faux_positifs: number
  corrigees: number
  revue_humaine: number
}

export interface Analyse {
  id: number
  projet_id: number
  etat: EtatAnalyse
  jetons_utilises: number
  cout_estime_usd: number
  message_erreur: string | null
  cree_le: string
  termine_le: string | null
  compteurs: Compteurs
}

export type EtatFaille =
  | 'en_attente'
  | 'en_cours'
  | 'confirmee'
  | 'faux_positif'
  | 'corrigee'
  | 'revue_humaine'

export type Famille = 'sqli' | 'commande' | 'secret' | 'traversee'

export interface Faille {
  id: number
  outils: string
  regle: string
  fichier: string
  ligne: number
  cwe: string
  famille: Famille
  gravite: 'haute' | 'moyenne' | 'basse'
  exposee: boolean
  priorite: number
  extrait: string
  exclue: boolean
  etat: EtatFaille
  point_entree: string | null
  justification: string | null
  tentatives_attaque: number
  tentatives_defense: number
  decision_revue: string | null
  commentaire_revue: string | null
}

export type NomAgent = 'attaquant' | 'defenseur' | 'orchestrateur'
export type NatureEtape =
  | 'raisonnement'
  | 'appel_outil'
  | 'resultat_outil'
  | 'verdict'
  | 'validation'
  | 'erreur'

export interface Etape {
  id?: number
  faille_id: number | null
  agent: NomAgent
  nature: NatureEtape
  resume: string
  outil: string | null
  succes: boolean
  cree_le?: string
}

// Messages reçus sur /ws/analyses/{id}
export type EvenementSuivi =
  | ({ type: 'etape' } & Etape)
  | { type: 'etat_faille'; faille_id: number; etat: EtatFaille }
  | { type: 'etat_analyse'; etat: EtatAnalyse; message?: string | null; compteurs?: Compteurs }

export const LIBELLES_FAMILLE: Record<Famille, string> = {
  sqli: 'Injection SQL (CWE-89)',
  commande: 'Injection de commandes (CWE-78)',
  secret: 'Secret codé en dur (CWE-798)',
  traversee: 'Traversée de répertoire (CWE-22)',
}

export const LIBELLES_ETAT_FAILLE: Record<EtatFaille, string> = {
  en_attente: 'En attente',
  en_cours: 'En cours',
  confirmee: 'Confirmée',
  faux_positif: 'Faux positif',
  corrigee: 'Corrigée',
  revue_humaine: 'Revue humaine',
}

export const LIBELLES_ETAT_ANALYSE: Record<EtatAnalyse, string> = {
  en_attente: 'En attente',
  preparation: 'Préparation',
  detection: 'Détection',
  selection: 'Sélection des alertes',
  traitement: 'Traitement par les agents',
  en_pause: 'En pause',
  terminee: 'Terminée',
  echec: 'Échec',
}
