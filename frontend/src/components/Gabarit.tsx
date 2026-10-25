import { Link, NavLink, Outlet, useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import { aLeRole, useSession } from '../auth'
import { ROUTES } from '../modules'

export function Gabarit() {
  const { utilisateur, fermer } = useSession()
  const naviguer = useNavigate()

  const menu = ROUTES.filter(
    (r) => r.menu && !r.publique && utilisateur && (!r.role || aLeRole(utilisateur, r.role)),
  )

  async function deconnexion() {
    try {
      await api.post('/api/auth/deconnexion')
    } catch {
      // la session est fermée côté client dans tous les cas
    }
    fermer()
    naviguer('/')
  }

  return (
    <div className="page">
      <header className="entete">
        <Link to="/" className="marque">
          <img src="/logo.svg" alt="" width={26} height={26} />
          PatchProof
        </Link>
        <nav className="menu">
          {menu.map((r) => (
            <NavLink key={r.chemin} to={r.chemin}>
              {r.menu}
            </NavLink>
          ))}
        </nav>
        {utilisateur && (
          <div className="compte">
            <span title={utilisateur.email}>{utilisateur.nom}</span>
            <button className="bouton discret" onClick={deconnexion}>
              Déconnexion
            </button>
          </div>
        )}
      </header>
      <main className="contenu">
        <Outlet />
      </main>
    </div>
  )
}
