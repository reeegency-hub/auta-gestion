import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { api, downloadAuthenticatedFile } from '../lib/api'
import { INVOICE_LABELS, money } from '../lib/labels'
import {
  Amount,
  Button,
  Card,
  EmptyState,
  ErrorBanner,
  LoadingBlock,
  PageHeader,
  PillSelector,
  StatusPill,
} from '../components/ui'

export default function InvoicesPage() {
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [busyId, setBusyId] = useState(null)
  const [params, setParams] = useSearchParams()
  const status = params.get('status') || ''

  async function load() {
    setLoading(true)
    const qs = status ? `?status=${status}` : ''
    try {
      setItems(await api(`/api/invoices${qs}`))
      setError('')
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [status])

  async function markPaid(inv) {
    setBusyId(inv.id)
    try {
      await api(`/api/invoices/${inv.id}/status`, { method: 'PATCH', body: { status: 'payee' } })
      await load()
    } catch (e) {
      setError(e.message)
    } finally {
      setBusyId(null)
    }
  }

  return (
    <div>
      <PageHeader title="Factures" subtitle="Historique et exports" />
      <ErrorBanner message={error} />

      <div className="mb-4">
        <PillSelector
          options={[
            { value: '', label: 'Toutes' },
            { value: 'en_attente', label: 'En attente' },
            { value: 'emise', label: 'Émise' },
            { value: 'payee', label: 'Payée' },
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
        <EmptyState title="Aucune facture" text="Convertissez un devis accepté en facture." />
      ) : (
        <div className="space-y-3">
          {items.map((inv) => (
            <Card key={inv.id} className="p-4">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-[16px] font-semibold">{inv.number}</p>
                  <Link
                    to={`/dossiers/${inv.dossier_id}?tab=facture`}
                    className="mt-0.5 text-[13px] font-medium text-primary"
                  >
                    Voir le dossier
                  </Link>
                </div>
                <StatusPill tone={inv.status === 'payee' ? 'ok' : 'warn'}>
                  {INVOICE_LABELS[inv.status] || inv.status}
                </StatusPill>
              </div>
              <div className="mt-3 flex items-center justify-between gap-2">
                <Amount value={money(inv.total_ttc)} highlight className="text-[20px]" />
                <div className="flex gap-2">
                  {inv.status !== 'payee' && (
                    <Button
                      variant="outline"
                      className="!min-h-[40px] !px-3 !py-2 text-[12px]"
                      disabled={busyId === inv.id}
                      onClick={() => markPaid(inv)}
                    >
                      Payée
                    </Button>
                  )}
                  <button
                    type="button"
                    className="min-h-[44px] px-2 text-[13px] font-semibold text-text-secondary"
                    onClick={() =>
                      downloadAuthenticatedFile(`/api/invoices/${inv.id}/pdf`, `${inv.number}.pdf`).catch(
                        (e) => setError(e.message)
                      )
                    }
                  >
                    PDF
                  </button>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
