import { Link, useParams } from 'react-router-dom'
import { telecharger } from '../../api/client'
import { useDonnees } from '../../api/useDonnees'
import { Chargement, MessageErreur } from '../../components/Etats'

interface RapportData {
  projet: string
  compteurs: { total: number; corrigees: number; faux_positifs: number; revue_humaine: number }
  cout_estime_usd: number
  failles: {
    id: number
    fichier: string
    ligne: number
    famille: string
    etat_libelle: string
    etat: string
    justification: string | null
    test_preuve: string | null
    correctif: { diff: string; explication: string } | null
  }[]
}

export default function Rapport() {
  const { id } = useParams()
  const { donnees, chargement, erreur } = useDonnees<RapportData>(`/api/analyses/${id}/rapport`)

  if (chargement) return <Chargement />
  if (erreur || !donnees) return <MessageErreur erreur={erreur ?? 'Rapport indisponible'} />

  return (
    <>
      <p className="legende">
        <Link to={`/analyses/${id}`}>← Analyse</Link>
      </p>
      <div className="ligne espace">
        <h1>Rapport — {donnees.projet}</h1>
        <button className="bouton" onClick={() => telecharger(`/api/analyses/${id}/rapport.pdf`, `rapport-${id}.pdf`)}>
          Exporter en PDF
        </button>
      </div>

      <div className="grille" style={{ margin: '1rem 0' }}>
        <Stat valeur={donnees.compteurs.total} libelle="Alertes" />
        <Stat valeur={donnees.compteurs.corrigees} libelle="Corrigées" />
        <Stat valeur={donnees.compteurs.faux_positifs} libelle="Faux positifs" />
        <Stat valeur={donnees.compteurs.revue_humaine} libelle="Revue humaine" />
        <Stat valeur={`${donnees.cout_estime_usd} $`} libelle="Coût" />
      </div>

      {donnees.failles.map((f) => (
        <section className="carte" key={f.id}>
          <div className="ligne espace">
            <h3>
              {f.fichier}:{f.ligne} — {f.famille}
            </h3>
            <span className={`badge etat-${f.etat}`}>{f.etat_libelle}</span>
          </div>
          {f.justification && <p>{f.justification}</p>}
          {f.test_preuve && (
            <details>
              <summary>Test de preuve</summary>
              <pre>{f.test_preuve}</pre>
            </details>
          )}
          {f.correctif && (
            <details>
              <summary>Correctif — {f.correctif.explication}</summary>
              <pre>{f.correctif.diff}</pre>
            </details>
          )}
        </section>
      ))}
    </>
  )
}

function Stat({ valeur, libelle }: { valeur: number | string; libelle: string }) {
  return (
    <div className="carte">
      <div className="chiffre">{valeur}</div>
      <div className="legende">{libelle}</div>
    </div>
  )
}
