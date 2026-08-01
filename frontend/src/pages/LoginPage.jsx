import { useState } from 'react'
import { Navigate, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { Button, ErrorBanner, Input } from '../components/ui'

export default function LoginPage() {
  const { user, loading: authLoading, login, register } = useAuth()
  const navigate = useNavigate()
  const [mode, setMode] = useState('login')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [form, setForm] = useState({
    email: import.meta.env.DEV ? 'directeur@auta.demo' : '',
    password: import.meta.env.DEV ? 'auta123' : '',
    full_name: '',
    garage_name: '',
  })

  if (authLoading) {
    return (
      <div className="flex min-h-[100dvh] items-center justify-center text-text-secondary">
        Chargement…
      </div>
    )
  }

  if (user) return <Navigate to="/" replace />

  async function onSubmit(e) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      if (mode === 'login') {
        await login(form.email, form.password)
      } else {
        await register({
          email: form.email,
          password: form.password,
          full_name: form.full_name,
          garage_name: form.garage_name,
        })
      }
      navigate('/')
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="app-frame flex min-h-[100dvh] flex-col">
      <div className="safe-top flex flex-1 flex-col justify-end bg-primary-dark px-5 pb-8 pt-14 text-white">
        <p className="text-[32px] font-bold leading-none tracking-tight">
          AUTA <span className="text-primary">Gestion</span>
        </p>
        <p className="mt-3 max-w-[280px] text-[15px] font-medium leading-snug text-white/70">
          Devis, atelier et factures — pensé pour le téléphone.
        </p>
      </div>

      <form
        onSubmit={onSubmit}
        className="safe-bottom animate-sheet space-y-3 rounded-t-[var(--radius-lg)] bg-white px-5 pb-8 pt-6"
      >
        <h1 className="!text-[20px]">{mode === 'login' ? 'Connexion' : 'Créer mon garage'}</h1>
        <ErrorBanner message={error} />
        {mode === 'register' && (
          <>
            <Input
              label="Nom du garage"
              value={form.garage_name}
              onChange={(e) => setForm({ ...form, garage_name: e.target.value })}
              required
              autoComplete="organization"
            />
            <Input
              label="Votre nom"
              value={form.full_name}
              onChange={(e) => setForm({ ...form, full_name: e.target.value })}
              required
              autoComplete="name"
            />
          </>
        )}
        <Input
          label="Email"
          type="email"
          inputMode="email"
          autoComplete="email"
          value={form.email}
          onChange={(e) => setForm({ ...form, email: e.target.value })}
          required
        />
        <Input
          label="Mot de passe"
          type="password"
          autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
          value={form.password}
          onChange={(e) => setForm({ ...form, password: e.target.value })}
          required
        />
        <Button type="submit" fullWidth disabled={loading}>
          {loading ? '…' : mode === 'login' ? 'Entrer' : 'Créer le compte'}
        </Button>
        <p className="pt-1 text-center text-[13px] font-medium text-text-secondary">
          {mode === 'login' ? (
            import.meta.env.DEV ? (
              <>
                Nouveau ?{' '}
                <button type="button" className="font-semibold text-primary" onClick={() => setMode('register')}>
                  S’inscrire (dev)
                </button>
              </>
            ) : (
              <span className="text-text-muted">Compte créé par l’administrateur du garage.</span>
            )
          ) : (
            <>
              Déjà un compte ?{' '}
              <button type="button" className="font-semibold text-primary" onClick={() => setMode('login')}>
                Se connecter
              </button>
            </>
          )}
        </p>
        {mode === 'login' && import.meta.env.DEV && (
          <p className="text-center text-[11px] text-text-muted">Démo : directeur@auta.demo / auta123</p>
        )}
      </form>
    </div>
  )
}
