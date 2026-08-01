import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../lib/api'
import { Button, Card, ErrorBanner, Input, LoadingBlock, PageHeader } from '../components/ui'

export default function SettingsPage() {
  const [form, setForm] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [saved, setSaved] = useState(false)
  const [pwd, setPwd] = useState({ current_password: '', new_password: '', confirm: '' })
  const [pwdMsg, setPwdMsg] = useState('')
  const [pwdErr, setPwdErr] = useState('')

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

  async function changePassword(e) {
    e.preventDefault()
    setPwdErr('')
    setPwdMsg('')
    if (pwd.new_password !== pwd.confirm) {
      setPwdErr('Les nouveaux mots de passe ne correspondent pas')
      return
    }
    try {
      await api('/api/auth/change-password', {
        method: 'POST',
        body: {
          current_password: pwd.current_password,
          new_password: pwd.new_password,
        },
      })
      setPwd({ current_password: '', new_password: '', confirm: '' })
      setPwdMsg('Mot de passe mis à jour.')
    } catch (err) {
      setPwdErr(err.message)
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
          <Input
            label="Téléphone (facture)"
            value={form.phone || ''}
            onChange={(e) => setForm({ ...form, phone: e.target.value })}
          />
          <Input
            label="Email (facture)"
            value={form.email || ''}
            onChange={(e) => setForm({ ...form, email: e.target.value })}
          />
          <div className="sm:col-span-2">
            <Input
              label="Adresse"
              value={form.address}
              onChange={(e) => setForm({ ...form, address: e.target.value })}
            />
          </div>
          <Input
            label="SIRET / SIREN"
            value={form.siret}
            onChange={(e) => setForm({ ...form, siret: e.target.value })}
          />
          <Input
            label="N° TVA"
            value={form.vat_number || ''}
            onChange={(e) => setForm({ ...form, vat_number: e.target.value })}
          />
          <Input
            label="N° RCS"
            value={form.rcs || ''}
            onChange={(e) => setForm({ ...form, rcs: e.target.value })}
          />
          <Input
            label="Mode de paiement (défaut)"
            value={form.payment_method || 'Chèque'}
            onChange={(e) => setForm({ ...form, payment_method: e.target.value })}
          />
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

      <Card className="mt-4 p-4">
        <h2 className="mb-3 text-[15px] font-semibold text-ink">Mot de passe</h2>
        <ErrorBanner message={pwdErr} />
        {pwdMsg && (
          <div className="mb-4 rounded-[var(--radius-sm)] bg-success-bg px-4 py-3 text-[13px] font-medium text-success">
            {pwdMsg}
          </div>
        )}
        <form onSubmit={changePassword} className="grid gap-3 sm:grid-cols-2">
          <Input
            label="Mot de passe actuel"
            type="password"
            autoComplete="current-password"
            value={pwd.current_password}
            onChange={(e) => setPwd({ ...pwd, current_password: e.target.value })}
            required
          />
          <div className="hidden sm:block" />
          <Input
            label="Nouveau mot de passe"
            type="password"
            autoComplete="new-password"
            value={pwd.new_password}
            onChange={(e) => setPwd({ ...pwd, new_password: e.target.value })}
            required
            minLength={6}
          />
          <Input
            label="Confirmer"
            type="password"
            autoComplete="new-password"
            value={pwd.confirm}
            onChange={(e) => setPwd({ ...pwd, confirm: e.target.value })}
            required
            minLength={6}
          />
          <div className="sm:col-span-2">
            <Button type="submit" fullWidth>
              Changer le mot de passe
            </Button>
          </div>
        </form>
      </Card>
    </div>
  )
}
