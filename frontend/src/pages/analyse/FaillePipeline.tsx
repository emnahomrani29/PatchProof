import { LIBELLES_FAMILLE, type EtatFaille, type Faille } from '../../api/types'

// Jalons du parcours d'une faille : détectée → Attaquant → (confirmée) → Défenseur → corrigée.
type Statut = 'attente' | 'cur' | 'ok' | 'ko' | 'warn'

function jalons(etat: EtatFaille, exclue: boolean): { texte: string; statut: Statut }[] {
  if (exclue) {
    return [
      { texte: 'Détectée', statut: 'ok' },
      { texte: 'Exclue', statut: 'warn' },
    ]
  }
  const detecte: Statut = 'ok'
  let attaquant: Statut = 'attente'
  let defenseur: Statut = 'attente'
  let final: { texte: string; statut: Statut } | null = null

  switch (etat) {
    case 'en_attente':
      attaquant = 'attente'
      break
    case 'en_cours':
      attaquant = 'cur'
      break
    case 'faux_positif':
      attaquant = 'ok'
      final = { texte: 'Faux positif', statut: 'ko' }
      break
    case 'confirmee':
      attaquant = 'ok'
      defenseur = 'cur'
      break
    case 'corrigee':
      attaquant = 'ok'
      defenseur = 'ok'
      final = { texte: 'Corrigée', statut: 'ok' }
      break
    case 'revue_humaine':
      attaquant = 'ok'
      defenseur = 'ko'
      final = { texte: 'Revue humaine', statut: 'warn' }
      break
  }

  const liste: { texte: string; statut: Statut }[] = [
    { texte: 'Détectée', statut: detecte },
    { texte: 'Attaquant', statut: attaquant },
  ]
  if (etat !== 'faux_positif' && etat !== 'en_cours' && etat !== 'en_attente') {
    liste.push({ texte: 'Défenseur', statut: defenseur })
  }
  if (final) liste.push(final)
  return liste
}

export function FaillePipeline({
  faille,
  etat,
  actif,
  onClic,
}: {
  faille: Faille
  etat: EtatFaille
  actif: boolean
  onClic: () => void
}) {
  return (
    <div
      className={`faille-carte ${actif || etat === 'en_cours' || etat === 'confirmee' ? 'en_cours' : ''}`}
      onClick={onClic}
      style={{ cursor: 'pointer' }}
    >
      <div className="ligne espace">
        <div>
          <strong>
            {faille.fichier}:{faille.ligne}
          </strong>
          <div className="legende">{LIBELLES_FAMILLE[faille.famille]}</div>
        </div>
        <span className={`gravite-${faille.gravite}`}>{faille.gravite}</span>
      </div>
      <div className="faille-chemin">
        {jalons(etat, faille.exclue).map((j, i, arr) => (
          <span key={j.texte} style={{ display: 'contents' }}>
            <span className={`jalon ${j.statut === 'attente' ? '' : j.statut}`}>{j.texte}</span>
            {i < arr.length - 1 && <span className="jalon-fleche">→</span>}
          </span>
        ))}
      </div>
    </div>
  )
}
