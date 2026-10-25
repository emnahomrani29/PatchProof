import type { RouteModule } from '../../modules'
import DetailProjet from './DetailProjet'
import ListeProjets from './ListeProjets'

export const routes: RouteModule[] = [
  { chemin: '/', element: <ListeProjets /> },
  { chemin: '/projets', element: <ListeProjets />, menu: 'Projets', ordre: 10 },
  { chemin: '/projets/:id', element: <DetailProjet /> },
]
