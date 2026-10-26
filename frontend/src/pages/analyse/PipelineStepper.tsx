import type { EtatAnalyse } from '../../api/types'

// Ordre des étapes d'une analyse, de l'import à la livraison.
const ETAPES: { cle: EtatAnalyse; libelle: string; icone: string }[] = [
  { cle: 'preparation', libelle: 'Préparation', icone: '📦' },
  { cle: 'detection', libelle: 'Détection', icone: '🔎' },
  { cle: 'selection', libelle: 'Sélection', icone: '✓' },
  { cle: 'traitement', libelle: 'Agents IA', icone: '🤖' },
  { cle: 'terminee', libelle: 'Terminé', icone: '🏁' },
]

const RANG: Record<string, number> = {
  en_attente: 0,
  preparation: 1,
  detection: 2,
  selection: 3,
  traitement: 4,
  terminee: 5,
  en_pause: 4,
  echec: -1,
}

/** Fil visuel des grandes étapes de l'analyse, avec l'étape courante animée. */
export function PipelineStepper({ etat }: { etat: EtatAnalyse }) {
  const rang = RANG[etat] ?? 0
  const echec = etat === 'echec'

  return (
    <div className="pipeline">
      {ETAPES.map((e) => {
        const r = RANG[e.cle]
        let classe = ''
        if (echec && e.cle === 'traitement') classe = 'echec'
        else if (r < rang) classe = 'faite'
        else if (r === rang) classe = 'active'
        return (
          <div key={e.cle} className={`etape-pipe ${classe}`}>
            <div className="pastille">{classe === 'faite' ? '✓' : e.icone}</div>
            <div className="libelle">{e.libelle}</div>
          </div>
        )
      })}
    </div>
  )
}
