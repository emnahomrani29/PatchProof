import type { RouteModule } from '../../modules'
import Admin from './Admin'

export const routes: RouteModule[] = [
  { chemin: '/admin', element: <Admin />, menu: 'Administration', ordre: 30, role: 'administrateur' },
]
