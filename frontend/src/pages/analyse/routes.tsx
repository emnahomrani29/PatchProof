import type { RouteModule } from '../../modules'
import Analyse from './Analyse'
import Rapport from './Rapport'

export const routes: RouteModule[] = [
  { chemin: '/analyses/:id', element: <Analyse /> },
  { chemin: '/analyses/:id/rapport', element: <Rapport /> },
]
