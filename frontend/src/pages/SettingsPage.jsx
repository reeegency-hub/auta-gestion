import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../lib/api'
import { Button, Card, ErrorBanner, Input, LoadingBlock, PageHeader } from '../components/ui'

export default function SettingsPage() {
  const [form, setForm] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    setLoading(true)
    api('/api/settings')
      .then(setForm)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  async function save(e) {
    e.preventDefault()
    setError('')
    setSaved(false)
    try {
      const { id, tenant_id, ...payload } = form
      const updated = await api('/api/settings', { method: 'PUT', body: payload })
      setForm(updated)
      setSaved(true)
    } catch (err) {
      setError(err.message)
    }
  }

  if (loading) return <LoadingBlock />
  if (!form) {
    return (
      <div>
        <PageHeader title="Paramètres" subtitle="Tarifs et identité du garage" />
        <ErrorBanner message={error || 'Impossible de charger les paramètres'} />
        <Button fullWidth onClick={() => window.location.reload()}>
          Réessayer
        </Button>
      </div>
    )
  }

  return (
    <div>
      <PageHeader title="Paramètres" subtitle="Tarifs et identité du garage" />
      <ErrorBanner message={error} />
      <div className="mb-4">
        <Link to="/catalogue" className="text-[13px] font-semibold text-primary">
          Catalogue pièces / stocks →
        </Link>
      </div>
      {saved && (
        <div className="mb-4 rounded-[var(--radius-sm)] bg-success-bg px-4 py-3 text-[13px] font-medium text-success">
          Paramètres enregistrés.
        </div>
      )}
      <Card className="p-4">
        <form onSubmit={save} className="grid gap-3 sm:grid-cols-2">
          <Input
            label="Raison sociale"
            value={form.company_name}
            onChange={(e) => setForm({ ...form, company_name: e.target.value })}
          />
          <div className="sm:col-span-2">
            <Input
              label="Adresse"
              value={form.address}
              onChange={(e) => setForm({ ...form, address: e.target.value })}
            />
          </div>
          <Input
            label="Taux carrosserie (€/h)"
            type="number"
            step="0.01"
            value={form.hourly_rate_carrosserie}
            onChange={(e) => setForm({ ...form, hourly_rate_carrosserie: Number(e.target.value) })}
          />
          <Input
            label="Taux peinture (€/h)"
            type="number"
            step="0.01"
            value={form.hourly_rate_peinture}
            onChange={(e) => setForm({ ...form, hourly_rate_peinture: Number(e.target.value) })}
          />
          <Input
            label="Taux mécanique (€/h)"
            type="number"
            step="0.01"
            value={form.hourly_rate_mecanique}
            onChange={(e) => setForm({ ...form, hourly_rate_mecanique: Number(e.target.value) })}
          />
          <Input
            label="TVA (%)"
            type="number"
            step="0.01"
            value={form.tva_rate}
            onChange={(e) => setForm({ ...form, tva_rate: Number(e.target.value) })}
          />
          <Input
            label="Consommables (€)"
            type="number"
            step="0.01"
            value={form.consumables_flat}
            onChange={(e) => setForm({ ...form, consumables_flat: Number(e.target.value) })}
          />
          <Input
            label="Marge pièces (%)"
            type="number"
            step="0.01"
            value={form.parts_margin_percent}
            onChange={(e) => setForm({ ...form, parts_margin_percent: Number(e.target.value) })}
          />
          <Input
            label="Forfait peinture (€)"
            type="number"
            step="0.01"
            value={form.forfait_peinture}
            onChange={(e) => setForm({ ...form, forfait_peinture: Number(e.target.value) })}
          />
          <div className="sm:col-span-2">
            <Button type="submit" fullWidth>
              Enregistrer
            </Button>
          </div>
        </form>
      </Card>
    </div>
  )
}
