import type { RouteModule } from '../../modules'
import Connexion from './Connexion'

export const routes: RouteModule[] = [
  { chemin: '/connexion', element: <Connexion />, publique: true },
]
