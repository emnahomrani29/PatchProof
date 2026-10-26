import { Link, useParams } from 'react-router-dom'
import { useDonnees } from '../../api/useDonnees'
import { BadgeAnalyse, Chargement, MessageErreur, Vide } from '../../components/Etats'
import type { Analyse, Projet } from '../../api/types'

export default function DetailProjet() {
  const { id } = useParams()
  const { donnees: projet } = useDonnees<Projet>(`/api/projets/${id}`)
  const { donnees: analyses, chargement, erreur } = useDonnees<Analyse[]>(`/api/projets/${id}/analyses`)

  return (
    <>
      <p className="legende">
        <Link to="/projets">← Projets</Link>
      </p>
      <h1>{projet?.nom ?? 'Projet'}</h1>
      {projet && (
        <p className="legende">
          {projet.framework} · {projet.nb_lignes} lignes · {projet.source}
        </p>
      )}
      <h2 style={{ marginTop: '1.5rem' }}>Historique des analyses</h2>
      <MessageErreur erreur={erreur} />
      {chargement ? (
        <Chargement />
      ) : !analyses?.length ? (
        <Vide texte="Aucune analyse lancée sur ce projet." />
      ) : (
        <table className="tableau">
          <thead>
            <tr>
              <th>#</th>
              <th>État</th>
              <th>Corrigées</th>
              <th>Faux positifs</th>
              <th>Coût</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {analyses.map((a) => (
              <tr key={a.id}>
                <td>{a.id}</td>
                <td>
                  <BadgeAnalyse etat={a.etat} />
                </td>
                <td>{a.compteurs.corrigees}</td>
                <td>{a.compteurs.faux_positifs}</td>
                <td>{a.cout_estime_usd.toFixed(3)} $</td>
                <td>
                  <Link to={`/analyses/${a.id}`}>Ouvrir</Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </>
  )
}
