import { useEffect, useState } from 'react'
import { api } from '../../api/client'
import { MessageErreur } from '../../components/Etats'

interface Correctif {
  id: number
  tentative: number
  diff: string
  explication: string
  valide: boolean
  decision: string
  resultat_validation: {
    preuve_bloquee: boolean
    tests_existants_ok: boolean
    alerte_disparue: boolean
    message: string
  }
}

interface Detail {
  fichier: string
  ligne: number
  cwe: string
  famille: string
  etat: string
  point_entree: string | null
  justification: string | null
  extrait: string
  test_preuve: { chemin: string; contenu: string } | null
  correctifs: Correctif[]
}

function Condition({ ok, texte }: { ok: boolean; texte: string }) {
  return (
    <span className={`badge ${ok ? 'etat-corrigee' : 'etat-revue_humaine'}`}>
      {ok ? '✓' : '✗'} {texte}
    </span>
  )
}

export function DetailFaille({ failleId, onDecision }: { failleId: number; onDecision?: () => void }) {
  const [detail, setDetail] = useState<Detail | null>(null)
  const [erreur, setErreur] = useState<unknown>(null)

  useEffect(() => {
    api
      .get<Detail>(`/api/failles/${failleId}/detail`)
      .then(setDetail)
      .catch(setErreur)
  }, [failleId])

  if (erreur) return <MessageErreur erreur={erreur} />
  if (!detail) return <p className="message discret">Chargement…</p>

  const correctif = detail.correctifs.find((c) => c.valide) ?? detail.correctifs[detail.correctifs.length - 1]

  async function decider(c: Correctif, decision: 'accepte' | 'rejete') {
    await api.patch(`/api/correctifs/${c.id}`, { decision })
    onDecision?.()
  }

  return (
    <div>
      <h3>
        {detail.fichier}:{detail.ligne} <span className="legende">· {detail.cwe}</span>
      </h3>
      {detail.point_entree && (
        <p className="legende">
          Point d'entrée : <code>{detail.point_entree}</code>
        </p>
      )}
      {detail.justification && <p>{detail.justification}</p>}

      {detail.test_preuve && (
        <>
          <h4>Test de preuve</h4>
          <pre>{detail.test_preuve.contenu}</pre>
        </>
      )}

      {correctif && (
        <>
          <h4>Correctif {correctif.valide ? '(validé)' : ''}</h4>
          <p>{correctif.explication}</p>
          <div className="ligne" style={{ gap: 6, marginBottom: 8 }}>
            <Condition ok={correctif.resultat_validation.preuve_bloquee} texte="faille bloquée" />
            <Condition ok={correctif.resultat_validation.tests_existants_ok} texte="tests au vert" />
            <Condition ok={correctif.resultat_validation.alerte_disparue} texte="alerte disparue" />
          </div>
          <pre>{correctif.diff}</pre>
          {correctif.valide && (
            <div className="ligne" style={{ gap: 8, marginTop: 8 }}>
              <span className="legende">Décision : {correctif.decision}</span>
              <button className="bouton" onClick={() => decider(correctif, 'accepte')}>
                Accepter
              </button>
              <button className="bouton danger" onClick={() => decider(correctif, 'rejete')}>
                Rejeter
              </button>
            </div>
          )}
        </>
      )}
    </div>
  )
}
