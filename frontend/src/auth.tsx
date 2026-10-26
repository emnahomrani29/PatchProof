import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { api, enregistrerJeton, lireJeton } from './api/client'
import type { Role, Utilisateur } from './api/types'

interface Session {
  utilisateur: Utilisateur | null
  chargement: boolean
  ouvrir: (jeton: string, utilisateur: Utilisateur) => void
  fermer: () => void
  rafraichir: () => Promise<void>
}

const ContexteSession = createContext<Session | null>(null)

const NIVEAUX: Record<Role, number> = { developpeur: 1, responsable_securite: 2, administrateur: 3 }

// eslint-disable-next-line react-refresh/only-export-components
export function aLeRole(utilisateur: Utilisateur | null, role: Role): boolean {
  return utilisateur !== null && NIVEAUX[utilisateur.role] >= NIVEAUX[role]
}

export function FournisseurSession({ children }: { children: ReactNode }) {
  const [utilisateur, setUtilisateur] = useState<Utilisateur | null>(null)
  const [chargement, setChargement] = useState(lireJeton() !== null)

  const rafraichir = useCallback(async () => {
    if (!lireJeton()) {
      setUtilisateur(null)
      return
    }
    try {
      setUtilisateur(await api.get<Utilisateur>('/api/auth/moi'))
    } catch {
      setUtilisateur(null)
    } finally {
      setChargement(false)
    }
  }, [])

  useEffect(() => {
    void rafraichir()
    const surDeconnexion = () => setUtilisateur(null)
    window.addEventListener('patchproof:deconnexion', surDeconnexion)
    return () => window.removeEventListener('patchproof:deconnexion', surDeconnexion)
  }, [rafraichir])

  const valeur = useMemo<Session>(
    () => ({
      utilisateur,
      chargement,
      ouvrir: (jeton, u) => {
        enregistrerJeton(jeton)
        setUtilisateur(u)
      },
      fermer: () => {
        enregistrerJeton(null)
        setUtilisateur(null)
      },
      rafraichir,
    }),
    [utilisateur, chargement, rafraichir],
  )

  return <ContexteSession.Provider value={valeur}>{children}</ContexteSession.Provider>
}

// eslint-disable-next-line react-refresh/only-export-components
export function useSession(): Session {
  const session = useContext(ContexteSession)
  if (!session) throw new Error('useSession doit être utilisé dans <FournisseurSession>')
  return session
}
