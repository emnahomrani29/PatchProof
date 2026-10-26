import type { ReactNode } from 'react'
import { Navigate, Route, Routes, useLocation } from 'react-router-dom'
import { aLeRole, useSession } from './auth'
import { Chargement } from './components/Etats'
import { Gabarit } from './components/Gabarit'
import { LimiteErreur } from './components/LimiteErreur'
import { ROUTES, type RouteModule } from './modules'

const CHEMIN_CONNEXION = '/connexion'

function Garde({ route }: { route: RouteModule }) {
  const { utilisateur, chargement } = useSession()
  if (route.publique) return <>{route.element}</>
  if (chargement) return <Chargement />
  if (!utilisateur) {
    const connexionDisponible = ROUTES.some((r) => r.chemin === CHEMIN_CONNEXION)
    return connexionDisponible ? <Navigate to={CHEMIN_CONNEXION} replace /> : <Accueil />
  }
  if (route.role && !aLeRole(utilisateur, route.role)) {
    return <p className="message erreur">Cette page est réservée au rôle « {route.role} ».</p>
  }
  return <ContenuProtege route={route}>{route.element}</ContenuProtege>
}

// Une erreur de rendu d'une page est isolée (clé = chemin) : elle n'emporte ni le menu ni le reste.
function ContenuProtege({ route, children }: { route: RouteModule; children: ReactNode }) {
  const emplacement = useLocation()
  return (
    <LimiteErreur key={`${route.chemin}:${emplacement.pathname}`}>{children}</LimiteErreur>
  )
}

function Accueil() {
  return (
    <section className="carte">
      <h1>PatchProof</h1>
      <p>
        Deux agents IA trient les alertes des scanners de sécurité : l'Attaquant prouve chaque faille par un test, le
        Défenseur la corrige, et le correctif n'est accepté que si les tests le prouvent.
      </p>
    </section>
  )
}

export default function App() {
  const accueilFourni = ROUTES.some((r) => r.chemin === '/')
  return (
    <Routes>
      <Route element={<Gabarit />}>
        {!accueilFourni && <Route path="/" element={<Accueil />} />}
        {ROUTES.map((r) => (
          <Route key={r.chemin} path={r.chemin} element={<Garde route={r} />} />
        ))}
        <Route path="*" element={<p className="message">Page introuvable.</p>} />
      </Route>
    </Routes>
  )
}
