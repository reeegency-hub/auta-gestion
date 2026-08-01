import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../lib/api'
import { useCoach } from '../components/Coach'
import { WORKSHOP_LABELS, WORKSHOP_TONES } from '../lib/labels'
import { Card, ErrorBanner, PageHeader, StatusPill } from '../components/ui'

const widgets = [
  { key: 'dossiers_en_cours', label: 'En cours', to: '/dossiers', tone: 'info' },
  { key: 'devis_en_attente', label: 'Devis', to: '/devis?status=en_attente', tone: 'warn' },
  { key: 'vehicules_en_atelier', label: 'Atelier', to: '/atelier', tone: 'info' },
  { key: 'pret_a_livrer', label: 'À livrer', to: '/atelier?focus=pret_a_livrer', tone: 'ok' },
  { key: 'factures_en_attente', label: 'Factures', to: '/factures?status=en_attente', tone: 'warn' },
]

export default function DashboardPage() {
  const [data, setData] = useState(null)
  const [recent, setRecent] = useState([])
  const [error, setError] = useState('')
  const coach = useCoach()

  useEffect(() => {
    api('/api/dashboard').then(setData).catch((e) => setError(e.message))
    api('/api/dossiers')
      .then((list) => setRecent(list.slice(0, 6)))
      .catch(() => {})
    coach.show('dashboard')
  }, [])

  return (
    <div>
      <PageHeader
        title="Accueil"
        subtitle="L’atelier en un coup d’œil"
        onHelp={() => coach.replay('dashboard')}
      />
      <ErrorBanner message={error} />

      <div className="scroll-x -mx-4 mb-5 px-4">
        {widgets.map((w) => (
          <Link key={w.key} to={w.to} className="block w-[132px]">
            <Card className="h-full p-3.5 active:scale-[0.98]">
              <p className="text-[11px] font-semibold uppercase tracking-wide text-text-muted">
                {w.label}
              </p>
              <p className="mt-2 text-[28px] font-bold leading-none tracking-tight">
                {data ? data[w.key] : '—'}
              </p>
              <div className="mt-3">
                <StatusPill tone={w.tone}>Ouvrir</StatusPill>
              </div>
            </Card>
          </Link>
        ))}
      </div>

      <div className="mb-3 flex items-center justify-between">
        <h2>Récents</h2>
        <Link to="/dossiers" className="text-[13px] font-semibold text-primary">
          Tout voir
        </Link>
      </div>
      <div className="space-y-2.5">
        {recent.map((d) => (
          <Link key={d.id} to={`/dossiers/${d.id}`} className="block">
            <Card className="flex items-center gap-3 p-3.5 active:bg-surface/60">
              <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-[12px] bg-info-bg text-[13px] font-bold text-primary">
                {(d.vehicle_make || 'V').slice(0, 1)}
              </div>
              <div className="min-w-0 flex-1">
                <p className="truncate text-[15px] font-semibold">
                  {d.vehicle_make} {d.vehicle_model}
                </p>
                <p className="truncate text-[12px] font-medium text-text-secondary">
                  {d.client_name} · {d.license_plate || d.reference}
                </p>
              </div>
              <StatusPill tone={WORKSHOP_TONES[d.workshop_status] || 'info'}>
                {WORKSHOP_LABELS[d.workshop_status]?.split(' ')[0] || d.reference}
              </StatusPill>
            </Card>
          </Link>
        ))}
        {recent.length === 0 && (
          <p className="text-[13px] text-text-muted">Aucun dossier pour le moment.</p>
        )}
      </div>

      <Link
        to="/dossiers?new=1"
        className="mt-5 flex min-h-[52px] items-center justify-center rounded-[var(--radius-md)] bg-primary text-[15px] font-semibold text-white active:brightness-95"
      >
        + Nouveau dossier
      </Link>
    </div>
  )
}
