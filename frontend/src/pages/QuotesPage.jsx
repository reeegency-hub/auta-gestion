import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { api, downloadAuthenticatedFile } from '../lib/api'
import { QUOTE_LABELS, QUOTE_TONES, money } from '../lib/labels'
import {
  Amount,
  Card,
  EmptyState,
  ErrorBanner,
  LoadingBlock,
  PageHeader,
  PillSelector,
  StatusPill,
} from '../components/ui'

export default function QuotesPage() {
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [params, setParams] = useSearchParams()
  const status = params.get('status') || ''

  useEffect(() => {
    setLoading(true)
    const qs = status ? `?status=${status}` : ''
    api(`/api/quotes${qs}`)
      .then(setItems)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [status])

  return (
    <div>
      <PageHeader title="Devis" subtitle="Suivi et exports PDF" />
      <ErrorBanner message={error} />

      <div className="mb-4">
        <PillSelector
          options={[
            { value: '', label: 'Tous' },
            ...Object.entries(QUOTE_LABELS).map(([k, v]) => ({ value: k, label: v })),
          ]}
          value={status}
          onChange={(v) => {
            setParams((prev) => {
              const n = new URLSearchParams(prev)
              if (v) n.set('status', v)
              else n.delete('status')
              return n
            })
          }}
        />
      </div>

      {loading ? (
        <LoadingBlock />
      ) : items.length === 0 ? (
        <EmptyState title="Aucun devis" text="Générez un devis depuis un dossier validé." />
      ) : (
        <div className="space-y-3">
          {items.map((q) => (
            <Card key={q.id} className="p-4">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-[16px] font-semibold">{q.number}</p>
                  <Link
                    to={`/dossiers/${q.dossier_id}`}
                    className="mt-0.5 text-[13px] font-medium text-primary"
                  >
                    Voir le dossier
                  </Link>
                </div>
                <StatusPill tone={QUOTE_TONES[q.status]}>{QUOTE_LABELS[q.status]}</StatusPill>
              </div>
              <div className="mt-3 flex items-center justify-between">
                <Amount value={money(q.total_ttc)} highlight className="text-[20px]" />
                <button
                  type="button"
                  className="min-h-[44px] px-2 text-[13px] font-semibold text-text-secondary"
                  onClick={() =>
                    downloadAuthenticatedFile(`/api/quotes/${q.id}/pdf`, `${q.number}.pdf`).catch((e) =>
                      setError(e.message)
                    )
                  }
                >
                  PDF
                </button>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
