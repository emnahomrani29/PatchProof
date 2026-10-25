import { useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api, telecharger } from '../../api/client'
import { useDonnees } from '../../api/useDonnees'
import { BadgeAnalyse, Chargement, MessageErreur } from '../../components/Etats'
import { type Analyse as TAnalyse, type EtatFaille, type Faille } from '../../api/types'
import { DetailFaille } from './DetailFaille'
import { FaillePipeline } from './FaillePipeline'
import { FluxAgents } from './FluxAgents'
import { PipelineStepper } from './PipelineStepper'
import { useSuivi } from './useSuivi'

const EN_COURS = new Set(['preparation', 'detection', 'traitement'])
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

  useEffect(() => {
    if (etat) {
      rechargerAnalyse()
      rechargerFailles()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [etat])

  const [maintenant, setMaintenant] = useState(Date.now())
  useEffect(() => {
    const t = setInterval(() => setMaintenant(Date.now()), 3_000)
    return () => clearInterval(t)
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

  // Faille sur laquelle un agent travaille en ce moment (dernière étape reçue).
  const failleActive = useMemo(() => {
    for (let i = suivi.etapes.length - 1; i >= 0; i--) {
      const fid = suivi.etapes[i].faille_id
      if (fid != null && (etatParFaille[fid] === 'en_cours' || etatParFaille[fid] === 'confirmee')) return fid
    }
    return null
  }, [suivi.etapes, etatParFaille])

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

  const etatCourant = etat ?? analyse.etat
  const enTraitement = EN_COURS.has(etatCourant) || suivi.etapes.length > 0

  return (
    <>
      <p className="legende">
        <Link to={`/projets/${analyse.projet_id}`}>← Projet</Link>
      </p>
      <div className="ligne espace">
        <h1>Analyse #{analyse.id}</h1>
        <div className="ligne">
          <BadgeAnalyse etat={etatCourant} />
          {suivi.connecte && (
            <span className="legende">
              <span className="ping" /> en direct
            </span>
          )}
        </div>
      </div>

      {/* Fil des grandes étapes */}
      <section className="carte">
        <PipelineStepper etat={etatCourant} />
        {EN_COURS.has(etatCourant) && (
          <p className="legende" style={{ textAlign: 'center', marginTop: 10 }}>
            {etatCourant === 'preparation' && 'Installation du projet et vérification des tests existants…'}
            {etatCourant === 'detection' && 'Analyse statique en cours : Bandit puis Semgrep, sans réseau…'}
            {etatCourant === 'traitement' && 'Les agents prouvent et corrigent les failles une par une…'}
          </p>
        )}
      </section>

      {suivi.message && etatCourant !== 'echec' && <p className="message">{suivi.message}</p>}
      {bloque && (
        <div className="ligne espace carte">
          <span>
            {etat === 'echec' || etat === 'en_pause'
              ? "L'analyse s'est arrêtée."
              : 'Aucune activité depuis plusieurs minutes : la tâche a probablement été interrompue.'}{' '}
            La relancer repart d'une liste d'alertes propre ; les failles déjà traitées ne sont pas refaites.
          </span>
          <button className="bouton secondaire" onClick={relancer}>
            Relancer l'analyse
          </button>
        </div>
      )}

      {/* Compteurs */}
      {compteurs && (
        <div className="grille" style={{ margin: '1rem 0' }}>
          <Stat valeur={compteurs.total} libelle="Alertes" />
          <Stat valeur={compteurs.confirmees} libelle="Confirmées" accent="var(--alerte)" />
          <Stat valeur={compteurs.corrigees} libelle="Corrigées" accent="var(--succes)" />
          <Stat valeur={compteurs.faux_positifs} libelle="Faux positifs" />
          <Stat valeur={compteurs.revue_humaine} libelle="Revue humaine" accent="var(--danger)" />
          <Stat valeur={`${analyse.cout_estime_usd.toFixed(3)} $`} libelle={`${analyse.jetons_utilises} jetons`} />
        </div>
      )}

      {etatCourant === 'selection' && (
        <div className="ligne espace carte">
          <span>Choisissez les alertes à traiter, puis lancez les agents.</span>
          <button className="bouton" onClick={demarrer}>
            🤖 Lancer les agents
          </button>
        </div>
      )}

      {/* Deux colonnes : parcours des failles | console des agents */}
      <div
        className="grille"
        style={{
          gridTemplateColumns: enTraitement ? 'minmax(0, 1fr) minmax(0, 1fr)' : '1fr',
          alignItems: 'start',
        }}
      >
        <section className="carte">
          <h2>Alertes {failleActive != null && <span className="legende">· agent actif</span>}</h2>
          <MessageErreur erreur={erreur} />
          {!failles?.length ? (
            <Chargement texte="Détection des alertes en cours…" />
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {failles.map((f) => (
                <div key={f.id}>
                  <FaillePipeline
                    faille={f}
                    etat={etatParFaille[f.id] ?? f.etat}
                    actif={failleActive === f.id}
                    onClic={() => setSelection(selection === f.id ? null : f.id)}
                  />
                  {etatCourant === 'selection' && (
                    <label className="legende" style={{ display: 'inline-flex', gap: 6, marginTop: 4 }}>
                      <input
                        type="checkbox"
                        checked={f.exclue}
                        onChange={(e) => exclure(f, e.target.checked)}
                      />
                      exclure cette alerte
                    </label>
                  )}
                  {selection === f.id && (
                    <div className="carte" style={{ marginTop: 8 }}>
                      <DetailFaille failleId={f.id} onDecision={rechargerFailles} />
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </section>

        {enTraitement && (
          <section className="carte">
            <div className="ligne espace">
              <h2>Suivi en direct</h2>
              {failleActive != null && (
                <span className="legende">
                  <span className="ping" /> alerte #{failleActive}
                </span>
              )}
            </div>
            <FluxAgents etapes={suivi.etapes} />
          </section>
        )}
      </div>

      {etatCourant === 'terminee' && (
        <section className="carte">
          <h2>Livraison</h2>
          <p className="legende">
            {compteurs?.corrigees ?? 0} corrigées · {compteurs?.faux_positifs ?? 0} faux positifs ·{' '}
            {compteurs?.revue_humaine ?? 0} en revue humaine
          </p>
          <div className="ligne" style={{ marginTop: 8 }}>
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

function Stat({ valeur, libelle, accent }: { valeur: number | string; libelle: string; accent?: string }) {
  return (
    <div className="carte">
      <div className="chiffre" style={accent ? { color: accent } : undefined}>
        {valeur}
      </div>
      <div className="legende">{libelle}</div>
    </div>
  )
}
