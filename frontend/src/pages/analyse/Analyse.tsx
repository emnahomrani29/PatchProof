import { useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api, telecharger } from '../../api/client'
import { useDonnees } from '../../api/useDonnees'
import { BadgeAnalyse, BadgeFaille, Chargement, MessageErreur } from '../../components/Etats'
import { LIBELLES_FAMILLE, type Analyse as TAnalyse, type EtatFaille, type Faille } from '../../api/types'
import { DetailFaille } from './DetailFaille'
import { FluxAgents } from './FluxAgents'
import { useSuivi } from './useSuivi'

const EN_COURS = new Set(['preparation', 'detection', 'traitement'])
/**
 * Silence toléré avant de considérer une analyse bloquée. La phase la plus silencieuse est
 * l'installation des dépendances, bornée à 300 s dans le bac à sable : au-delà de six minutes sans
 * le moindre événement, la tâche a été abandonnée.
 */
const DELAI_SILENCE_MS = 360_000

export default function Analyse() {
  const { id } = useParams()
  const analyseId = Number(id)
  const {
    donnees: analyse,
    erreur: erreurAnalyse,
    chargement: chargementAnalyse,
    recharger: rechargerAnalyse,
  } = useDonnees<TAnalyse>(`/api/analyses/${analyseId}`)
  const { donnees: failles, recharger: rechargerFailles, erreur } = useDonnees<Faille[]>(
    `/api/analyses/${analyseId}/failles`,
  )
  const [selection, setSelection] = useState<number | null>(null)

  const suivi = useSuivi(analyseId, analyse != null)
  const etat = suivi.etatAnalyse ?? analyse?.etat ?? null
  const compteurs = suivi.compteurs ?? analyse?.compteurs ?? null

  // Quand l'analyse change d'état (via WebSocket), on rafraîchit les listes.
  useEffect(() => {
    if (etat) {
      rechargerAnalyse()
      rechargerFailles()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [etat])

  // Une analyse dont la tâche a été abandonnée (conteneur redémarré pendant l'analyse) reste
  // bloquée dans son dernier état. La préparation et la détection publient des étapes de
  // progression : une longue absence d'événement signale donc un vrai problème, et l'utilisateur
  // se voit proposer une relance plutôt qu'un chargement sans fin.
  const [maintenant, setMaintenant] = useState(Date.now())
  useEffect(() => {
    const minuterie = setInterval(() => setMaintenant(Date.now()), 5_000)
    return () => clearInterval(minuterie)
  }, [])
  const bloque =
    etat === 'echec' ||
    etat === 'en_pause' ||
    (EN_COURS.has(etat ?? '') && maintenant - suivi.dernierSignal > DELAI_SILENCE_MS)

  const etatParFaille = useMemo(() => {
    const m: Record<number, EtatFaille> = {}
    failles?.forEach((f) => (m[f.id] = suivi.etatsFailles[f.id] ?? f.etat))
    return m
  }, [failles, suivi.etatsFailles])

  async function exclure(f: Faille, exclue: boolean) {
    await api.patch(`/api/failles/${f.id}`, { exclue })
    rechargerFailles()
  }

  async function demarrer() {
    await api.post(`/api/analyses/${analyseId}/demarrer`)
    rechargerAnalyse()
  }

  async function relancer() {
    await api.post(`/api/analyses/${analyseId}/relancer`)
    rechargerAnalyse()
    rechargerFailles()
  }

  if (!analyse) {
    if (erreurAnalyse && !chargementAnalyse) return <MessageErreur erreur={erreurAnalyse} />
    return <Chargement />
  }

  return (
    <>
      <p className="legende">
        <Link to={`/projets/${analyse.projet_id}`}>← Projet</Link>
      </p>
      <div className="ligne espace">
        <h1>Analyse #{analyse.id}</h1>
        <div className="ligne">
          <BadgeAnalyse etat={etat ?? analyse.etat} />
          {suivi.connecte && <span className="legende">● en direct</span>}
        </div>
      </div>
      {suivi.message && <p className="message">{suivi.message}</p>}
      {bloque && (
        <div className="ligne espace carte">
          <span>
            {etat === 'echec' || etat === 'en_pause'
              ? "L'analyse s'est arrêtée."
              : "Aucune activité depuis plusieurs minutes : la tâche a probablement été interrompue."}{' '}
            La relancer repart d'une liste d'alertes propre, et les failles déjà traitées ne sont pas
            refaites.
          </span>
          <button className="bouton secondaire" onClick={relancer}>
            Relancer l'analyse
          </button>
        </div>
      )}

      {compteurs && (
        <div className="grille" style={{ margin: '1rem 0' }}>
          <Stat valeur={compteurs.total} libelle="Alertes" />
          <Stat valeur={compteurs.confirmees} libelle="Confirmées" />
          <Stat valeur={compteurs.corrigees} libelle="Corrigées" />
          <Stat valeur={compteurs.faux_positifs} libelle="Faux positifs" />
          <Stat valeur={compteurs.revue_humaine} libelle="Revue humaine" />
        </div>
      )}

      {etat === 'selection' && (
        <div className="ligne espace carte">
          <span>Choisissez les alertes à traiter, puis lancez les agents.</span>
          <button className="bouton" onClick={demarrer}>
            Lancer les agents
          </button>
        </div>
      )}

      <div className="grille" style={{ gridTemplateColumns: EN_COURS.has(etat ?? '') || etat === 'traitement' ? '1fr 1fr' : '1fr', alignItems: 'start' }}>
        <section className="carte">
          <h2>Alertes</h2>
          <MessageErreur erreur={erreur} />
          {!failles?.length ? (
            <Chargement texte="Détection des alertes en cours…" />
          ) : (
            <table className="tableau">
              <thead>
                <tr>
                  <th>Fichier</th>
                  <th>Famille</th>
                  <th>Gravité</th>
                  <th>État</th>
                  {etat === 'selection' && <th>Exclure</th>}
                </tr>
              </thead>
              <tbody>
                {failles.map((f) => (
                  <tr key={f.id} onClick={() => setSelection(f.id)} style={{ cursor: 'pointer' }}>
                    <td>
                      {f.fichier}:{f.ligne}
                    </td>
                    <td>{LIBELLES_FAMILLE[f.famille]}</td>
                    <td className={`gravite-${f.gravite}`}>{f.gravite}</td>
                    <td>
                      <BadgeFaille etat={etatParFaille[f.id] ?? f.etat} />
                    </td>
                    {etat === 'selection' && (
                      <td onClick={(e) => e.stopPropagation()}>
                        <input
                          type="checkbox"
                          checked={f.exclue}
                          onChange={(e) => exclure(f, e.target.checked)}
                        />
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>

        {(EN_COURS.has(etat ?? '') || suivi.etapes.length > 0) && (
          <section className="carte">
            <h2>Suivi en direct</h2>
            <FluxAgents etapes={suivi.etapes} />
          </section>
        )}
      </div>

      {selection != null && (
        <section className="carte">
          <div className="ligne espace">
            <h2>Détail de l'alerte</h2>
            <button className="bouton discret" onClick={() => setSelection(null)}>
              Fermer
            </button>
          </div>
          <DetailFaille failleId={selection} onDecision={rechargerFailles} />
        </section>
      )}

      {etat === 'terminee' && (
        <section className="carte">
          <h2>Livraison</h2>
          <div className="ligne">
            <Link className="bouton secondaire" to={`/analyses/${analyse.id}/rapport`}>
              Voir le rapport
            </Link>
            <button
              className="bouton secondaire"
              onClick={() => telecharger(`/api/analyses/${analyse.id}/rapport.pdf`, `rapport-${analyse.id}.pdf`)}
            >
              Rapport PDF
            </button>
            <button
              className="bouton secondaire"
              onClick={() => telecharger(`/api/analyses/${analyse.id}/patch`, `patchproof-${analyse.id}.patch`)}
            >
              Télécharger le patch
            </button>
          </div>
        </section>
      )}
    </>
  )
}

function Stat({ valeur, libelle }: { valeur: number; libelle: string }) {
  return (
    <div className="carte">
      <div className="chiffre">{valeur}</div>
      <div className="legende">{libelle}</div>
    </div>
  )
}
