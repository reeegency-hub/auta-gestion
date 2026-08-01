const TOKEN_KEY = 'auta_token'

/** En prod : VITE_API_URL=https://ton-api.onrender.com — en local : proxy Vite (/api). */
export const API_BASE = (import.meta.env.VITE_API_URL || '').replace(/\/$/, '')

export function apiUrl(path) {
  if (path.startsWith('http')) return path
  return `${API_BASE}${path}`
}

export function getToken() {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token) {
  localStorage.setItem(TOKEN_KEY, token)
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY)
}

function formatDetail(detail) {
  if (!detail) return 'Une erreur est survenue'
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    return detail
      .map((d) => (typeof d === 'string' ? d : d.msg || JSON.stringify(d)))
      .join(' · ')
  }
  return 'Une erreur est survenue'
}

function loginPath() {
  // HashRouter en prod Pages → /auta-gestion/#/login
  if (import.meta.env.VITE_API_URL || (import.meta.env.BASE_URL || '/') !== '/') {
    const base = (import.meta.env.BASE_URL || '/').replace(/\/?$/, '/')
    return `${window.location.origin}${base}#/login`
  }
  return '/login'
}

export async function api(path, options = {}) {
  const headers = { ...(options.headers || {}) }
  const token = getToken()
  if (token) headers.Authorization = `Bearer ${token}`
  if (options.body && !(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json'
    options.body = JSON.stringify(options.body)
  }

  let res
  try {
    res = await fetch(apiUrl(path), { ...options, headers })
  } catch {
    throw new Error('Connexion impossible. Vérifie ton réseau ou que le serveur est démarré.')
  }

  if (res.status === 401) {
    clearToken()
    if (!path.includes('/auth/login') && !path.includes('/auth/register')) {
      const from = encodeURIComponent(window.location.pathname + window.location.search)
      window.location.href = `${loginPath()}?from=${from}`
    }
  }
  if (!res.ok) {
    let detail = 'Erreur serveur'
    try {
      const data = await res.json()
      detail = formatDetail(data.detail)
    } catch {
      /* ignore */
    }
    throw new Error(detail)
  }
  if (res.status === 204) return null
  const ct = res.headers.get('content-type') || ''
  if (ct.includes('application/json')) return res.json()
  return res.blob()
}

export function authHeaders() {
  const token = getToken()
  return token ? { Authorization: `Bearer ${token}` } : {}
}

export async function downloadAuthenticatedFile(path, filename) {
  let res
  try {
    res = await fetch(apiUrl(path), { headers: authHeaders() })
  } catch {
    throw new Error('Téléchargement impossible (hors ligne ?)')
  }
  if (res.status === 401) {
    clearToken()
    window.location.href = loginPath()
    throw new Error('Session expirée')
  }
  if (!res.ok) {
    let detail = 'Fichier introuvable'
    try {
      const data = await res.json()
      detail = formatDetail(data.detail)
    } catch {
      /* ignore */
    }
    throw new Error(detail)
  }
  const blob = await res.blob()
  const ct = res.headers.get('content-type') || ''
  if (ct.includes('application/json')) {
    throw new Error('Le serveur n’a pas renvoyé un fichier PDF')
  }
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename || 'document.pdf'
  a.rel = 'noopener'
  document.body.appendChild(a)
  a.click()
  a.remove()
  setTimeout(() => URL.revokeObjectURL(url), 1500)
}

export async function fetchAuthenticatedBlob(path) {
  const res = await fetch(apiUrl(path), { headers: authHeaders() })
  if (res.status === 401) {
    clearToken()
    throw new Error('Session expirée')
  }
  if (!res.ok) throw new Error('Fichier introuvable')
  return res.blob()
}
