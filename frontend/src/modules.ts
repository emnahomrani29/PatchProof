// Chaque module déclare ses pages dans src/pages/<module>/routes.tsx (export `routes`).
// Elles sont découvertes automatiquement : ajouter un module ne demande pas de modifier App.tsx.

import type { ReactNode } from 'react'
import type { Role } from './api/types'

export interface RouteModule {
  chemin: string
  element: ReactNode
  /** Libellé dans le menu ; absent = page non listée dans le menu. */
  menu?: string
  /** Position dans le menu (croissante). */
  ordre?: number
  /** Accessible sans être connecté (connexion, inscription). */
  publique?: boolean
  /** Rôle minimal pour accéder à la page. */
  role?: Role
}

const fichiers = import.meta.glob<{ routes: RouteModule[] }>('./pages/*/routes.tsx', { eager: true })

export const ROUTES: RouteModule[] = Object.values(fichiers)
  .flatMap((f) => f.routes)
  .sort((a, b) => (a.ordre ?? 100) - (b.ordre ?? 100))
