import { useCallback, useEffect, useState } from 'react'
import { api } from './client'

/** Charge une ressource GET et expose son état. `chemin = null` suspend le chargement. */
export function useDonnees<T>(chemin: string | null) {
  const [donnees, setDonnees] = useState<T | null>(null)
  const [erreur, setErreur] = useState<unknown>(null)
  const [chargement, setChargement] = useState(chemin !== null)

  const recharger = useCallback(async () => {
    if (chemin === null) return
    setChargement(true)
    try {
      setDonnees(await api.get<T>(chemin))
      setErreur(null)
    } catch (e) {
      setErreur(e)
    } finally {
      setChargement(false)
    }
  }, [chemin])

  useEffect(() => {
    void recharger()
  }, [recharger])

  return { donnees, setDonnees, erreur, chargement, recharger }
}
