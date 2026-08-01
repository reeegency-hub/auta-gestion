import { NavLink, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

const tabs = [
  {
    to: '/',
    label: 'Accueil',
    end: true,
    icon: (active) => (
      <svg width="22" height="22" viewBox="0 0 24 24" fill={active ? 'currentColor' : 'none'} stroke="currentColor" strokeWidth="2">
        <path d="M4 10.5L12 4l8 6.5V20a1 1 0 0 1-1 1h-5v-6H10v6H5a1 1 0 0 1-1-1v-9.5z" strokeLinejoin="round" />
      </svg>
    ),
  },
  {
    to: '/dossiers',
    label: 'Dossiers',
    icon: (active) => (
      <svg width="22" height="22" viewBox="0 0 24 24" fill={active ? 'currentColor' : 'none'} stroke="currentColor" strokeWidth="2">
        <path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7z" strokeLinejoin="round" />
      </svg>
    ),
  },
  {
    to: '/atelier',
    label: 'Atelier',
    icon: (active) => (
      <svg width="22" height="22" viewBox="0 0 24 24" fill={active ? 'currentColor' : 'none'} stroke="currentColor" strokeWidth="2">
        <circle cx="12" cy="12" r="8" />
        <circle cx="12" cy="12" r="3" fill={active ? 'currentColor' : 'none'} />
      </svg>
    ),
  },
  {
    to: '/devis',
    label: 'Devis',
    icon: (active) => (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M7 3h8l4 4v14a1 1 0 0 1-1 1H7a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1z" strokeLinejoin="round" />
        <path d="M15 3v4h4M9 13h6M9 17h4" strokeLinecap="round" />
      </svg>
    ),
  },
  {
    to: '/factures',
    label: 'Factures',
    icon: (active) => (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M6 3h12v18l-2-1.5L14 21l-2-1.5L10 21l-2-1.5L6 21V3z" strokeLinejoin="round" />
        <path d="M9 9h6M9 13h6" strokeLinecap="round" />
      </svg>
    ),
  },
]

export default function AppShell() {
  const { user, logout } = useAuth()
  const location = useLocation()

  return (
    <div className="app-frame flex flex-col">
      <header className="safe-top sticky top-0 z-40 border-b border-border/80 bg-white/95 backdrop-blur-md">
        <div className="flex items-center justify-between gap-3 px-4 py-3">
          <NavLink to="/" className="min-w-0" end>
            <p className="truncate text-[18px] font-bold tracking-tight text-primary-dark">
              AUTA <span className="text-primary">Gestion</span>
            </p>
            <p className="truncate text-[12px] font-medium text-text-muted">
              {user?.full_name}
            </p>
          </NavLink>
          <div className="flex shrink-0 items-center gap-2">
            <NavLink
              to="/parametres"
              className="flex h-10 w-10 items-center justify-center rounded-full bg-surface text-text-secondary"
              aria-label="Réglages"
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="3" />
                <path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" strokeLinecap="round" />
              </svg>
            </NavLink>
            <button
              type="button"
              onClick={logout}
              className="h-10 rounded-full bg-surface px-3 text-[12px] font-semibold text-text-secondary"
            >
              Déconnexion
            </button>
          </div>
        </div>
      </header>

      <main
        className="flex-1 overflow-y-auto px-4 pb-[calc(88px+env(safe-area-inset-bottom))] pt-4"
        key={location.pathname}
      >
        <Outlet />
      </main>

      <nav
        className="safe-bottom fixed bottom-0 left-1/2 z-40 w-full max-w-[430px] -translate-x-1/2 border-t border-border bg-white/95 px-1 pt-1 backdrop-blur-md"
        style={{ ['--nav-h']: '72px' }}
      >
        <div className="flex">
          {tabs.map((l) => (
            <NavLink
              key={l.to}
              to={l.to}
              end={l.end}
              className={({ isActive }) =>
                `flex min-h-[56px] flex-1 flex-col items-center justify-center gap-1 rounded-[12px] text-[10px] font-semibold ${
                  isActive ? 'text-primary' : 'text-text-muted'
                }`
              }
            >
              {({ isActive }) => (
                <>
                  <span className={`flex h-8 w-8 items-center justify-center rounded-full ${isActive ? 'bg-info-bg' : ''}`}>
                    {l.icon(isActive)}
                  </span>
                  {l.label}
                </>
              )}
            </NavLink>
          ))}
        </div>
      </nav>
    </div>
  )
}
