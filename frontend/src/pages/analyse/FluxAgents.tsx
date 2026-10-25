import { useEffect, useRef } from 'react'
import type { Etape as EtapeAgent } from '../../api/types'

const ICONE: Record<string, string> = {
  raisonnement: '💭',
  appel_outil: '🔧',
  resultat_outil: '↩',
  verdict: '⚖',
  validation: '✓',
  erreur: '⚠',
}

const COULEUR_AGENT: Record<string, string> = {
  attaquant: 'var(--danger)',
  defenseur: 'var(--accent)',
  orchestrateur: 'var(--texte-2)',
}

/** Journal défilant des étapes des agents, mis à jour en direct. */
export function FluxAgents({ etapes }: { etapes: EtapeAgent[] }) {
  const finRef = useRef<HTMLDivElement>(null)
  useEffect(() => finRef.current?.scrollIntoView({ behavior: 'smooth' }), [etapes.length])

  if (!etapes.length) {
    return <p className="message discret">En attente des premières étapes des agents…</p>
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6, maxHeight: 460, overflowY: 'auto' }}>
      {etapes.map((e, i) => (
        <div
          key={e.id ?? i}
          className="carte"
          style={{ padding: '8px 12px', margin: 0, borderLeft: `3px solid ${COULEUR_AGENT[e.agent]}` }}
        >
          <div className="ligne" style={{ gap: 8 }}>
            <span>{ICONE[e.nature] ?? '·'}</span>
            <strong style={{ color: COULEUR_AGENT[e.agent], textTransform: 'capitalize', fontSize: '.85rem' }}>
              {e.agent}
            </strong>
            {e.outil && <code style={{ fontSize: '.8rem' }}>{e.outil}</code>}
            {!e.succes && <span className="badge etat-revue_humaine">échec</span>}
          </div>
          <div style={{ fontSize: '.9rem', marginTop: 2 }}>{e.resume}</div>
        </div>
      ))}
      <div ref={finRef} />
    </div>
  )
}
