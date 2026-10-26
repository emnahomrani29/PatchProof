import type { EtatAnalyse, EtatFaille } from '../api/types'
import { LIBELLES_ETAT_ANALYSE, LIBELLES_ETAT_FAILLE } from '../api/types'

export function Chargement({ texte = 'Chargement…' }: { texte?: string }) {
  return <p className="message discret">{texte}</p>
}

export function MessageErreur({ erreur }: { erreur: unknown }) {
  if (!erreur) return null
  const texte = erreur instanceof Error ? erreur.message : String(erreur)
  return (
    <p className="message erreur" role="alert">
      {texte}
    </p>
  )
}

export function Vide({ texte }: { texte: string }) {
  return <p className="message discret">{texte}</p>
}

export function BadgeFaille({ etat }: { etat: EtatFaille }) {
  return <span className={`badge etat-${etat}`}>{LIBELLES_ETAT_FAILLE[etat]}</span>
}

export function BadgeAnalyse({ etat }: { etat: EtatAnalyse }) {
  return <span className={`badge analyse-${etat}`}>{LIBELLES_ETAT_ANALYSE[etat]}</span>
}
