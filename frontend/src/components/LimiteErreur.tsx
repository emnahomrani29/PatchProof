import { Component, type ErrorInfo, type ReactNode } from 'react'

interface Props {
  children: ReactNode
}
interface State {
  erreur: Error | null
}

/**
 * Capture toute erreur de rendu d'un sous-arbre React et affiche un message au lieu d'une page
 * blanche. Sans cela, une seule exception pendant le rendu démonte toute l'application.
 */
export class LimiteErreur extends Component<Props, State> {
  state: State = { erreur: null }

  static getDerivedStateFromError(erreur: Error): State {
    return { erreur }
  }

  componentDidCatch(erreur: Error, infos: ErrorInfo) {
    // Visible dans la console du navigateur pour le diagnostic.
    console.error('Erreur de rendu PatchProof :', erreur, infos.componentStack)
  }

  reinitialiser = () => this.setState({ erreur: null })

  render() {
    if (this.state.erreur) {
      return (
        <section className="carte" style={{ maxWidth: 680, margin: '3rem auto' }}>
          <h1>Une erreur est survenue sur cette page</h1>
          <p>L'affichage a rencontré un problème, mais l'analyse continue côté serveur.</p>
          <pre style={{ color: 'var(--danger)' }}>{this.state.erreur.message}</pre>
          <div className="ligne" style={{ marginTop: '1rem' }}>
            <button className="bouton" onClick={this.reinitialiser}>
              Réessayer l'affichage
            </button>
            <button className="bouton secondaire" onClick={() => window.location.reload()}>
              Recharger la page
            </button>
          </div>
        </section>
      )
    }
    return this.props.children
  }
}
