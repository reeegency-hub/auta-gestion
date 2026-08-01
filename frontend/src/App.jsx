import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider, useAuth } from './context/AuthContext'
import { CoachProvider } from './components/Coach'
import OfflineBanner from './components/OfflineBanner'
import AppShell from './components/AppShell'
import LoginPage from './pages/LoginPage'
import DashboardPage from './pages/DashboardPage'
import DossiersPage from './pages/DossiersPage'
import DossierDetailPage from './pages/DossierDetailPage'
import WorkshopPage from './pages/WorkshopPage'
import QuotesPage from './pages/QuotesPage'
import InvoicesPage from './pages/InvoicesPage'
import SettingsPage from './pages/SettingsPage'
import CatalogPage from './pages/CatalogPage'

function Protected({ children }) {
  const { user, loading } = useAuth()
  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center text-text-secondary">
        Chargement…
      </div>
    )
  }
  if (!user) return <Navigate to="/login" replace />
  return children
}

export default function App() {
  const basename = (import.meta.env.BASE_URL || '/').replace(/\/$/, '') || '/'
  return (
    <AuthProvider>
      <CoachProvider>
        <BrowserRouter basename={basename === '/' ? undefined : basename}>
          <OfflineBanner />
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route
              path="/"
              element={
                <Protected>
                  <AppShell />
                </Protected>
              }
            >
              <Route index element={<DashboardPage />} />
              <Route path="dossiers" element={<DossiersPage />} />
              <Route path="dossiers/:id" element={<DossierDetailPage />} />
              <Route path="atelier" element={<WorkshopPage />} />
              <Route path="devis" element={<QuotesPage />} />
              <Route path="factures" element={<InvoicesPage />} />
              <Route path="catalogue" element={<CatalogPage />} />
              <Route path="parametres" element={<SettingsPage />} />
            </Route>
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
      </CoachProvider>
    </AuthProvider>
  )
}
