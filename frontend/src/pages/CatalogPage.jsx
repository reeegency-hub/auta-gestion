import { useEffect, useState } from 'react'
import { api } from '../lib/api'
import { money } from '../lib/labels'
import {
  Amount,
  Button,
  Card,
  EmptyState,
  ErrorBanner,
  Input,
  LoadingBlock,
  PageHeader,
} from '../components/ui'

const empty = { sku: '', label: '', unit_price: 0, stock_qty: 0 }

export default function CatalogPage() {
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [form, setForm] = useState(empty)
  const [busy, setBusy] = useState(false)

  async function load() {
    setLoading(true)
    try {
      setItems(await api('/api/catalog/parts'))
      setError('')
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  async function create(e) {
    e.preventDefault()
    setBusy(true)
    try {
      await api('/api/catalog/parts', { method: 'POST', body: form })
      setForm(empty)
      await load()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div>
      <PageHeader title="Catalogue pièces" subtitle="Références et stocks" />
      <ErrorBanner message={error} />

      <Card className="mb-4 p-4">
        <form className="space-y-3" onSubmit={create}>
          <Input
            label="Libellé"
            value={form.label}
            onChange={(e) => setForm({ ...form, label: e.target.value })}
            required
            placeholder="Ex. Pare-chocs avant"
          />
          <div className="grid grid-cols-2 gap-2">
            <Input
              label="Réf. / SKU"
              value={form.sku}
              onChange={(e) => setForm({ ...form, sku: e.target.value })}
            />
            <Input
              label="Prix €"
              type="number"
              step="0.01"
              value={form.unit_price}
              onChange={(e) => setForm({ ...form, unit_price: Number(e.target.value) })}
            />
          </div>
          <Input
            label="Stock"
            type="number"
            step="1"
            value={form.stock_qty}
            onChange={(e) => setForm({ ...form, stock_qty: Number(e.target.value) })}
          />
          <Button fullWidth type="submit" disabled={busy}>
            Ajouter
          </Button>
        </form>
      </Card>

      {loading ? (
        <LoadingBlock />
      ) : items.length === 0 ? (
        <EmptyState title="Catalogue vide" text="Ajoutez vos pièces courantes." />
      ) : (
        <div className="space-y-2">
          {items.map((p) => (
            <Card key={p.id} className="flex items-center justify-between gap-3 p-3.5">
              <div className="min-w-0">
                <p className="truncate text-[14px] font-semibold">{p.label}</p>
                <p className="text-[12px] text-text-muted">
                  {p.sku || '—'} · stock {p.stock_qty}
                </p>
              </div>
              <Amount value={money(p.unit_price)} />
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
