import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, ErreurApi } from '../../api/client'
import { useSession } from '../../auth'
import type { Utilisateur } from '../../api/types'

type Mode = 'connexion' | 'inscription'

export default function Connexion() {
  const { ouvrir } = useSession()
  const naviguer = useNavigate()
  const [mode, setMode] = useState<Mode>('connexion')
  const [nom, setNom] = useState('')
  const [email, setEmail] = useState('')
  const [motDePasse, setMotDePasse] = useState('')
  const [erreur, setErreur] = useState<string | null>(null)
  const [occupe, setOccupe] = useState(false)

  async function soumettre(e: FormEvent) {
    e.preventDefault()
    setErreur(null)
    setOccupe(true)
    try {
      if (mode === 'inscription') {
        await api.post('/api/auth/inscription', { nom, email, mot_de_passe: motDePasse })
      }
      const { jeton, utilisateur } = await api.post<{ jeton: string; utilisateur: Utilisateur }>(
        '/api/auth/connexion',
        { email, mot_de_passe: motDePasse },
      )
      ouvrir(jeton, utilisateur)
      naviguer('/projets')
    } catch (err) {
      setErreur(err instanceof ErreurApi ? err.message : 'Une erreur est survenue.')
    } finally {
      setOccupe(false)
    }
  }

  return (
    <section className="carte" style={{ maxWidth: 460, margin: '3rem auto' }}>
      <h1>{mode === 'connexion' ? 'Connexion' : 'Créer un compte'}</h1>
      <form className="formulaire" onSubmit={soumettre}>
        {mode === 'inscription' && (
          <label className="champ">
            Nom
            <input value={nom} onChange={(e) => setNom(e.target.value)} required minLength={2} />
          </label>
        )}
        <label className="champ">
          E-mail
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        </label>
        <label className="champ">
          Mot de passe
          <input
            type="password"
            value={motDePasse}
            onChange={(e) => setMotDePasse(e.target.value)}
            required
            minLength={8}
          />
        </label>
        {erreur && <p className="message erreur">{erreur}</p>}
        <button className="bouton" disabled={occupe}>
          {occupe ? '…' : mode === 'connexion' ? 'Se connecter' : "S'inscrire"}
        </button>
      </form>
      <p className="legende" style={{ marginTop: '1rem' }}>
        {mode === 'connexion' ? 'Pas encore de compte ? ' : 'Déjà un compte ? '}
        <button
          className="bouton discret"
          onClick={() => {
            setMode(mode === 'connexion' ? 'inscription' : 'connexion')
            setErreur(null)
          }}
        >
          {mode === 'connexion' ? "S'inscrire" : 'Se connecter'}
        </button>
      </p>
    </section>
  )
}
