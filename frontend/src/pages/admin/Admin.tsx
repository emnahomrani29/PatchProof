import { useEffect, useState } from 'react'
import { api } from '../../api/client'
import { Chargement, MessageErreur } from '../../components/Etats'
import type { Role, Utilisateur } from '../../api/types'

interface Parametres {
  budget_jetons_analyse: number
  max_tentatives_agent: number
  max_appels_outils_faille: number
  modele_attaquant: string
  modele_defenseur: string
  modele_leger: string
}

const ROLES: Role[] = ['developpeur', 'responsable_securite', 'administrateur']

export default function Admin() {
  const [params, setParams] = useState<Parametres | null>(null)
  const [utilisateurs, setUtilisateurs] = useState<Utilisateur[]>([])
  const [message, setMessage] = useState<string | null>(null)
  const [erreur, setErreur] = useState<unknown>(null)

  useEffect(() => {
    api
      .get<Parametres>('/api/admin/parametres')
      .then(setParams)
      .catch(setErreur)
    api
      .get<Utilisateur[]>('/api/admin/utilisateurs')
      .then(setUtilisateurs)
      .catch(setErreur)
  }, [])

  async function enregistrer() {
    if (!params) return
    await api.put('/api/admin/parametres', params)
    setMessage('Paramètres enregistrés.')
    setTimeout(() => setMessage(null), 2500)
  }

  async function changerRole(u: Utilisateur, role: Role) {
    const maj = await api.patch<Utilisateur>(`/api/admin/utilisateurs/${u.id}`, { role })
    setUtilisateurs((liste) => liste.map((x) => (x.id === maj.id ? maj : x)))
  }

  if (erreur) return <MessageErreur erreur={erreur} />
  if (!params) return <Chargement />

  const champ = (cle: keyof Parametres, libelle: string, type = 'number') => (
    <label className="champ">
      {libelle}
      <input
        type={type}
        value={params[cle]}
        onChange={(e) =>
          setParams({ ...params, [cle]: type === 'number' ? Number(e.target.value) : e.target.value })
        }
      />
    </label>
  )

  return (
    <>
      <h1>Administration</h1>

      <section className="carte">
        <h2>Limites et modèles</h2>
        <div className="grille">
          {champ('budget_jetons_analyse', 'Budget de jetons / analyse')}
          {champ('max_tentatives_agent', 'Tentatives par agent')}
          {champ('max_appels_outils_faille', "Appels d'outils / faille")}
          {champ('modele_attaquant', 'Modèle Attaquant', 'text')}
          {champ('modele_defenseur', 'Modèle Défenseur', 'text')}
          {champ('modele_leger', 'Modèle léger', 'text')}
        </div>
        <div className="ligne" style={{ marginTop: '1rem' }}>
          <button className="bouton" onClick={enregistrer}>
            Enregistrer
          </button>
          {message && <span className="message succes">{message}</span>}
        </div>
      </section>

      <section className="carte">
        <h2>Utilisateurs</h2>
        <table className="tableau">
          <thead>
            <tr>
              <th>Nom</th>
              <th>E-mail</th>
              <th>Rôle</th>
            </tr>
          </thead>
          <tbody>
            {utilisateurs.map((u) => (
              <tr key={u.id}>
                <td>{u.nom}</td>
                <td>{u.email}</td>
                <td>
                  <select value={u.role} onChange={(e) => changerRole(u, e.target.value as Role)}>
                    {ROLES.map((r) => (
                      <option key={r} value={r}>
                        {r}
                      </option>
                    ))}
                  </select>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </>
  )
}
