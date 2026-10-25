import { useEffect, useRef, useState } from 'react'
import type { Etape as EtapeAgent } from '../../api/types'

const ICONE: Record<string, string> = {
  raisonnement: '💭',
  appel_outil: '🔧',
  resultat_outil: '↩',
  verdict: '⚖',
  validation: '✅',
  erreur: '⚠',
  information: 'ℹ️',
}

const LIBELLE_NATURE: Record<string, string> = {
  raisonnement: 'réflexion',
  appel_outil: 'outil',
  resultat_outil: 'résultat',
  verdict: 'verdict',
  validation: 'validation',
  erreur: 'erreur',
  information: 'info',
}

function heure(iso?: string): string {
  if (!iso) return ''
  const d = new Date(iso)
  return Number.isNaN(d.getTime()) ? '' : d.toLocaleTimeString('fr-FR')
}

/** Console défilante des étapes des agents, enrichie (détails dépliables, horodatage). */
export function FluxAgents({ etapes, filtre }: { etapes: EtapeAgent[]; filtre?: number | null }) {
  const finRef = useRef<HTMLDivElement>(null)
  const [auto, setAuto] = useState(true)
  const liste = filtre == null ? etapes : etapes.filter((e) => e.faille_id === filtre)

  useEffect(() => {
    if (auto) finRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [liste.length, auto])

  if (!liste.length) {
    return <p className="message discret">En attente des premières étapes des agents…</p>
  }

  return (
    <div
      className="console"
      onScroll={(e) => {
        const el = e.currentTarget
        setAuto(el.scrollHeight - el.scrollTop - el.clientHeight < 60)
      }}
    >
      {liste.map((e, i) => {
        const detail = e.nature === 'resultat_outil' || e.nature === 'raisonnement' ? e.resultat : null
        return (
          <div key={e.id ?? i} className={`evt ${e.agent}`}>
            <div className="evt-tete">
              <span>{ICONE[e.nature] ?? '·'}</span>
              <span className="evt-agent">{e.agent}</span>
              <span className="legende">· {LIBELLE_NATURE[e.nature] ?? e.nature}</span>
              {e.outil && <span className="evt-outil">{e.outil}</span>}
              {!e.succes && <span className="jalon ko">échec</span>}
              <span className="evt-heure">{heure(e.cree_le)}</span>
            </div>
            <div className="evt-resume">{e.resume}</div>
            {detail && detail !== e.resume && <pre className="evt-detail">{detail}</pre>}
          </div>
        )
      })}
      <div ref={finRef} />
    </div>
  )
}
