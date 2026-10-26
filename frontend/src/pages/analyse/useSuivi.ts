import { useEffect, useRef, useState } from 'react'
import { api, urlWebSocket } from '../../api/client'
import type { Compteurs, Etape as EtapeAgent, EtatAnalyse, EtatFaille, EvenementSuivi } from '../../api/types'

export interface EtatSuivi {
  etapes: EtapeAgent[]
  etatsFailles: Record<number, EtatFaille>
  etatAnalyse: EtatAnalyse | null
  compteurs: Compteurs | null
  message: string | null
  connecte: boolean
  /** Horodatage du dernier signe de vie reçu (connexion, étape ou changement d'état). */
  dernierSignal: number
}

/** Délais de reconnexion : un redémarrage de l'API ne doit pas interrompre le suivi. */
const ATTENTES_RECONNEXION_MS = [1_000, 2_000, 4_000, 8_000, 10_000]
/** Code de fermeture renvoyé par l'API quand le jeton est refusé : inutile d'insister. */
const FERMETURE_NON_AUTHENTIFIE = 4401

/**
 * S'abonne au flux WebSocket d'une analyse et accumule les événements reçus.
 *
 * L'historique déjà enregistré est chargé à l'ouverture : un rechargement de page en pleine
 * analyse ne doit pas faire disparaître les étapes déjà affichées.
 */
export function useSuivi(analyseId: number, actif: boolean): EtatSuivi {
  const [etapes, setEtapes] = useState<EtapeAgent[]>([])
  const [etatsFailles, setEtatsFailles] = useState<Record<number, EtatFaille>>({})
  const [etatAnalyse, setEtatAnalyse] = useState<EtatAnalyse | null>(null)
  const [compteurs, setCompteurs] = useState<Compteurs | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [connecte, setConnecte] = useState(false)
  const [dernierSignal, setDernierSignal] = useState(Date.now())
  const socketRef = useRef<WebSocket | null>(null)
  const tentative = useRef(0)
  const minuterie = useRef<number | null>(null)

  useEffect(() => {
    if (!actif) return
    api
      .get<EtapeAgent[]>(`/api/analyses/${analyseId}/etapes`)
      .then((historique) => setEtapes((recues) => (recues.length ? recues : historique)))
      .catch(() => undefined)
  }, [analyseId, actif])

  useEffect(() => {
    if (!actif) return
    let ferme = false

    function connecter() {
      const socket = new WebSocket(urlWebSocket(`/ws/analyses/${analyseId}`))
      socketRef.current = socket

      socket.onopen = () => {
        tentative.current = 0
        setConnecte(true)
        setDernierSignal(Date.now())
      }

      socket.onmessage = (ev) => {
        setDernierSignal(Date.now())
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

      socket.onclose = (ev) => {
        setConnecte(false)
        if (ferme || ev.code === FERMETURE_NON_AUTHENTIFIE) return
        const delai =
          ATTENTES_RECONNEXION_MS[Math.min(tentative.current, ATTENTES_RECONNEXION_MS.length - 1)]
        tentative.current += 1
        minuterie.current = window.setTimeout(connecter, delai)
      }

      socket.onerror = () => socket.close()
    }

    connecter()
    return () => {
      ferme = true
      if (minuterie.current !== null) window.clearTimeout(minuterie.current)
      socketRef.current?.close()
    }
  }, [analyseId, actif])

  return { etapes, etatsFailles, etatAnalyse, compteurs, message, connecte, dernierSignal }
}
