import { useState } from 'react'
import { api } from '../../api/client'
import { useDonnees } from '../../api/useDonnees'
import { Chargement, MessageErreur, Vide } from '../../components/Etats'
import { DetailFaille } from '../analyse/DetailFaille'
import { LIBELLES_FAMILLE, type Faille } from '../../api/types'

export default function Revue() {
  const { donnees: failles, chargement, erreur, recharger } = useDonnees<Faille[]>('/api/revue')
  const [selection, setSelection] = useState<number | null>(null)
  const [commentaire, setCommentaire] = useState('')

  async function decider(failleId: number, decision: string) {
    await api.post(`/api/failles/${failleId}/revue`, {
      decision,
      commentaire: commentaire || 'Traité en revue humaine.',
    })
    setSelection(null)
    setCommentaire('')
    recharger()
  }

  return (
    <>
      <h1>Revue humaine</h1>
      <p className="legende">Failles que les agents n'ont pas pu corriger automatiquement.</p>
      <MessageErreur erreur={erreur} />
      {chargement ? (
        <Chargement />
      ) : !failles?.length ? (
        <Vide texte="Aucune faille en attente de revue." />
      ) : (
        <table className="tableau">
          <thead>
            <tr>
              <th>Fichier</th>
              <th>Famille</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {failles.map((f) => (
              <tr key={f.id}>
                <td>
                  {f.fichier}:{f.ligne}
                </td>
                <td>{LIBELLES_FAMILLE[f.famille]}</td>
                <td>
                  <button className="bouton discret" onClick={() => setSelection(f.id)}>
                    Examiner
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {selection != null && (
        <section className="carte">
          <div className="ligne espace">
            <h2>Examen de l'alerte</h2>
            <button className="bouton discret" onClick={() => setSelection(null)}>
              Fermer
            </button>
          </div>
          <DetailFaille failleId={selection} />
          <label className="champ" style={{ marginTop: '1rem' }}>
            Commentaire
            <textarea value={commentaire} onChange={(e) => setCommentaire(e.target.value)} rows={2} />
          </label>
          <div className="ligne">
            <button className="bouton" onClick={() => decider(selection, 'corrigee_manuellement')}>
              Corrigée manuellement
            </button>
            <button className="bouton secondaire" onClick={() => decider(selection, 'faux_positif')}>
              Faux positif
            </button>
            <button className="bouton danger" onClick={() => decider(selection, 'acceptee_risque')}>
              Risque accepté
            </button>
          </div>
        </section>
      )}
    </>
  )
}
