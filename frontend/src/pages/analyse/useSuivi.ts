import { useEffect, useRef, useState } from 'react'
import { urlWebSocket } from '../../api/client'
import type { Compteurs, Etape as EtapeAgent, EtatAnalyse, EtatFaille, EvenementSuivi } from '../../api/types'

export interface EtatSuivi {
  etapes: EtapeAgent[]
  etatsFailles: Record<number, EtatFaille>
  etatAnalyse: EtatAnalyse | null
  compteurs: Compteurs | null
  message: string | null
  connecte: boolean
}

/** S'abonne au flux WebSocket d'une analyse et accumule les événements reçus. */
export function useSuivi(analyseId: number, actif: boolean): EtatSuivi {
  const [etapes, setEtapes] = useState<EtapeAgent[]>([])
  const [etatsFailles, setEtatsFailles] = useState<Record<number, EtatFaille>>({})
  const [etatAnalyse, setEtatAnalyse] = useState<EtatAnalyse | null>(null)
  const [compteurs, setCompteurs] = useState<Compteurs | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [connecte, setConnecte] = useState(false)
  const socketRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    if (!actif) return
    const socket = new WebSocket(urlWebSocket(`/ws/analyses/${analyseId}`))
    socketRef.current = socket
    socket.onopen = () => setConnecte(true)
    socket.onclose = () => setConnecte(false)
    socket.onmessage = (ev) => {
      const e: EvenementSuivi = JSON.parse(ev.data)
      if (e.type === 'etape') {
        setEtapes((liste) => [...liste, e])
      } else if (e.type === 'etat_faille') {
        setEtatsFailles((m) => ({ ...m, [e.faille_id]: e.etat }))
      } else if (e.type === 'etat_analyse') {
        setEtatAnalyse(e.etat)
        if (e.compteurs) setCompteurs(e.compteurs)
        setMessage(e.message ?? null)
      }
    }
    return () => socket.close()
  }, [analyseId, actif])

  return { etapes, etatsFailles, etatAnalyse, compteurs, message, connecte }
}
