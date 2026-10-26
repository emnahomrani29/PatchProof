import type { RouteModule } from '../../modules'
import Revue from './Revue'

export const routes: RouteModule[] = [
  { chemin: '/revue', element: <Revue />, menu: 'Revue', ordre: 20, role: 'responsable_securite' },
]
