import { useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api, ErreurApi } from '../../api/client'
import { useDonnees } from '../../api/useDonnees'
import { Chargement, MessageErreur, Vide } from '../../components/Etats'
import type { Projet } from '../../api/types'

export default function ListeProjets() {
  const { donnees: projets, chargement, erreur, recharger } = useDonnees<Projet[]>('/api/projets')
  const [url, setUrl] = useState('')
  const [occupe, setOccupe] = useState(false)
  const [messageImport, setMessageImport] = useState<string | null>(null)
  const fichierRef = useRef<HTMLInputElement>(null)
  const naviguer = useNavigate()

  async function importerGithub() {
    setOccupe(true)
    setMessageImport(null)
    try {
      await api.post('/api/projets', { url_github: url.trim() })
      setUrl('')
      await recharger()
    } catch (e) {
      setMessageImport(e instanceof ErreurApi ? e.message : 'Import impossible.')
    } finally {
      setOccupe(false)
    }
  }

  async function importerZip(fichier: File) {
    setOccupe(true)
    setMessageImport(null)
    const corps = new FormData()
    corps.append('fichier', fichier)
    try {
      await api.post('/api/projets/zip', corps)
      await recharger()
    } catch (e) {
      setMessageImport(e instanceof ErreurApi ? e.message : 'Import impossible.')
    } finally {
      setOccupe(false)
    }
  }

  async function lancerAnalyse(projet: Projet) {
    const analyse = await api.post<{ id: number }>(`/api/projets/${projet.id}/analyses`)
    naviguer(`/analyses/${analyse.id}`)
  }

  async function connecterGithub() {
    const { url } = await api.get<{ url: string }>('/api/auth/github')
    window.location.href = url
  }

  return (
    <>
      <div className="ligne espace">
        <h1>Mes projets</h1>
        <button className="bouton secondaire" onClick={connecterGithub}>
          Connecter GitHub
        </button>
      </div>

      <section className="carte">
        <h2>Importer un projet</h2>
        <div className="ligne" style={{ alignItems: 'flex-end' }}>
          <label className="champ" style={{ flex: 1, minWidth: 280 }}>
            Dépôt GitHub public
            <input
              placeholder="https://github.com/org/depot"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
            />
          </label>
          <button className="bouton" disabled={occupe || !url.trim()} onClick={importerGithub}>
            Importer
          </button>
          <span className="legende">ou</span>
          <input
            ref={fichierRef}
            type="file"
            accept=".zip"
            hidden
            onChange={(e) => e.target.files?.[0] && importerZip(e.target.files[0])}
          />
          <button className="bouton secondaire" disabled={occupe} onClick={() => fichierRef.current?.click()}>
            Archive ZIP
          </button>
        </div>
        {occupe && <Chargement texte="Import et analyse du projet…" />}
        {messageImport && <p className="message erreur">{messageImport}</p>}
      </section>

      <MessageErreur erreur={erreur} />
      {chargement ? (
        <Chargement />
      ) : !projets?.length ? (
        <Vide texte="Aucun projet pour le moment. Importez votre premier dépôt ci-dessus." />
      ) : (
        <table className="tableau">
          <thead>
            <tr>
              <th>Nom</th>
              <th>Framework</th>
              <th>Lignes</th>
              <th>Source</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {projets.map((p) => (
              <tr key={p.id}>
                <td>
                  <Link to={`/projets/${p.id}`}>{p.nom}</Link>
                </td>
                <td>{p.framework}</td>
                <td>{p.nb_lignes}</td>
                <td>{p.source}</td>
                <td>
                  <button className="bouton" onClick={() => lancerAnalyse(p)}>
                    Analyser
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </>
  )
}
