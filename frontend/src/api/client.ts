// Client HTTP unique : ajoute le jeton, convertit les erreurs {detail, code} en ErreurApi.

export const URL_API: string = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

const CLE_JETON = 'patchproof.jeton'

export function lireJeton(): string | null {
  try {
    return localStorage.getItem(CLE_JETON)
  } catch {
    return null
  }
}

export function enregistrerJeton(jeton: string | null): void {
  try {
    if (jeton) localStorage.setItem(CLE_JETON, jeton)
    else localStorage.removeItem(CLE_JETON)
  } catch {
    // stockage indisponible (navigation privée) : la session durera le temps de l'onglet
  }
}

export class ErreurApi extends Error {
  readonly statut: number
  readonly code: string

  constructor(message: string, statut: number, code: string) {
    super(message)
    this.statut = statut
    this.code = code
  }
}

type Corps = BodyInit | object | undefined

async function requete<T>(methode: string, chemin: string, corps?: Corps): Promise<T> {
  const entetes: Record<string, string> = {}
  const jeton = lireJeton()
  if (jeton) entetes.Authorization = `Bearer ${jeton}`

  let body: BodyInit | undefined
  if (corps instanceof FormData || typeof corps === 'string') {
    body = corps
  } else if (corps !== undefined) {
    entetes['Content-Type'] = 'application/json'
    body = JSON.stringify(corps)
  }

  let reponse: Response
  try {
    reponse = await fetch(`${URL_API}${chemin}`, { method: methode, headers: entetes, body })
  } catch {
    throw new ErreurApi("Impossible de joindre l'API. Est-elle lancée ?", 0, 'reseau')
  }

  if (reponse.status === 401) {
    enregistrerJeton(null)
    window.dispatchEvent(new Event('patchproof:deconnexion'))
  }
  if (!reponse.ok) {
    let detail = `Erreur ${reponse.status}`
    let code = 'erreur'
    try {
      const json = await reponse.json()
      if (typeof json.detail === 'string') detail = json.detail
      else if (Array.isArray(json.detail)) detail = json.detail.map((d: { msg: string }) => d.msg).join(' ; ')
      if (json.code) code = json.code
    } catch {
      // corps non JSON
    }
    throw new ErreurApi(detail, reponse.status, code)
  }
  if (reponse.status === 204) return undefined as T

  const type = reponse.headers.get('content-type') ?? ''
  if (type.includes('application/json')) return (await reponse.json()) as T
  return (await reponse.text()) as T
}

export const api = {
  get: <T>(chemin: string) => requete<T>('GET', chemin),
  post: <T>(chemin: string, corps?: Corps) => requete<T>('POST', chemin, corps),
  put: <T>(chemin: string, corps?: Corps) => requete<T>('PUT', chemin, corps),
  patch: <T>(chemin: string, corps?: Corps) => requete<T>('PATCH', chemin, corps),
  delete: <T>(chemin: string) => requete<T>('DELETE', chemin),
}

/** Télécharge un fichier protégé (PDF, patch) en conservant l'authentification. */
export async function telecharger(chemin: string, nomFichier: string): Promise<void> {
  const jeton = lireJeton()
  const reponse = await fetch(`${URL_API}${chemin}`, {
    headers: jeton ? { Authorization: `Bearer ${jeton}` } : {},
  })
  if (!reponse.ok) throw new ErreurApi(`Téléchargement impossible (${reponse.status})`, reponse.status, 'telechargement')
  const url = URL.createObjectURL(await reponse.blob())
  const lien = document.createElement('a')
  lien.href = url
  lien.download = nomFichier
  lien.click()
  URL.revokeObjectURL(url)
}

export function urlWebSocket(chemin: string): string {
  const base = URL_API.replace(/^http/, 'ws')
  const jeton = lireJeton() ?? ''
  return `${base}${chemin}?jeton=${encodeURIComponent(jeton)}`
}
