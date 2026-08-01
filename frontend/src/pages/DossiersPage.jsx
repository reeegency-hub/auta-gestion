import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { api } from '../lib/api'
import { useCoach } from '../components/Coach'
import { WORKSHOP_LABELS, WORKSHOP_TONES } from '../lib/labels'
import {
  BottomSheet,
  Button,
  Card,
  EmptyState,
  ErrorBanner,
  Input,
  LoadingBlock,
  PageHeader,
  SearchInput,
  StatusPill,
  TextArea,
} from '../components/ui'

const emptyForm = {
  client: { first_name: '', last_name: '', email: '', phone: '', address: '' },
  vehicle_make: '',
  vehicle_model: '',
  vehicle_year: '',
  license_plate: '',
  vin: '',
  insurance_name: '',
  insurance_claim_number: '',
  comments: '',
}

export default function DossiersPage() {
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)
  const [q, setQ] = useState('')
  const [error, setError] = useState('')
  const [sheet, setSheet] = useState(false)
  const [form, setForm] = useState(emptyForm)
  const [busy, setBusy] = useState(false)
  const [params, setParams] = useSearchParams()
  const navigate = useNavigate()
  const coach = useCoach()
  const debounceRef = useRef(null)

  async function load(search = q) {
    setLoading(true)
    try {
      const data = await api(`/api/dossiers${search ? `?q=${encodeURIComponent(search)}` : ''}`)
      setItems(data)
      setError('')
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
    coach.show('dossiers')
    if (params.get('new') === '1') {
      setSheet(true)
      params.delete('new')
      setParams(params, { replace: true })
    }
  }, [])

  useEffect(() => {
    clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => {
      load(q)
    }, 300)
    return () => clearTimeout(debounceRef.current)
  }, [q])

  async function createDossier(e) {
    e.preventDefault()
    setError('')
    setBusy(true)
    try {
      const d = await api('/api/dossiers', { method: 'POST', body: form })
      setSheet(false)
      setForm(emptyForm)
      navigate(`/dossiers/${d.id}`)
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div>
      <PageHeader
        title="Dossiers"
        subtitle="Clients et véhicules"
        onHelp={() => coach.replay('dossiers')}
      />
      <ErrorBanner message={error} />

      <div className="mb-4">
        <SearchInput
          value={q}
          onChange={setQ}
          onSubmit={() => load()}
          placeholder="Immat, client, réf…"
        />
      </div>

      {loading && items.length === 0 ? (
        <LoadingBlock />
      ) : items.length === 0 ? (
        <EmptyState title="Aucun dossier" text="Créez un dossier pour démarrer." />
      ) : (
        <div className="space-y-2.5">
          {items.map((d) => (
            <Link key={d.id} to={`/dossiers/${d.id}`}>
              <Card className="mb-2.5 p-3.5">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="truncate text-[15px] font-semibold">
                      {d.vehicle_make} {d.vehicle_model}
                    </p>
                    <p className="mt-0.5 truncate text-[12px] font-medium text-text-secondary">
                      {d.client_name} · {d.license_plate || d.reference}
                    </p>
                  </div>
                  <StatusPill tone={WORKSHOP_TONES[d.workshop_status]}>
                    {WORKSHOP_LABELS[d.workshop_status]}
                  </StatusPill>
                </div>
              </Card>
            </Link>
          ))}
        </div>
      )}

      <button
        type="button"
        onClick={() => setSheet(true)}
        className="fab fixed bottom-[calc(88px+env(safe-area-inset-bottom))] right-[max(16px,calc(50%-215px+16px))] z-30 flex h-14 w-14 items-center justify-center rounded-full bg-primary text-2xl text-white shadow-lg"
        aria-label="Nouveau dossier"
      >
        +
      </button>

      <BottomSheet
        open={sheet}
        onClose={() => setSheet(false)}
        title="Nouveau dossier"
        footer={
          <>
            <Button fullWidth type="submit" form="new-dossier" disabled={busy}>
              Créer
            </Button>
            <Button variant="ghost" fullWidth onClick={() => setSheet(false)}>
              Annuler
            </Button>
          </>
        }
      >
        <form id="new-dossier" className="space-y-3" onSubmit={createDossier}>
          <div className="grid grid-cols-2 gap-2">
            <Input
              label="Prénom"
              value={form.client.first_name}
              onChange={(e) =>
                setForm({ ...form, client: { ...form.client, first_name: e.target.value } })
              }
              required
            />
            <Input
              label="Nom"
              value={form.client.last_name}
              onChange={(e) =>
                setForm({ ...form, client: { ...form.client, last_name: e.target.value } })
              }
              required
            />
          </div>
          <Input
            label="Téléphone"
            value={form.client.phone}
            onChange={(e) => setForm({ ...form, client: { ...form.client, phone: e.target.value } })}
          />
          <div className="grid grid-cols-2 gap-2">
            <Input
              label="Marque"
              value={form.vehicle_make}
              onChange={(e) => setForm({ ...form, vehicle_make: e.target.value })}
            />
            <Input
              label="Modèle"
              value={form.vehicle_model}
              onChange={(e) => setForm({ ...form, vehicle_model: e.target.value })}
            />
          </div>
          <Input
            label="Immatriculation"
            value={form.license_plate}
            onChange={(e) => setForm({ ...form, license_plate: e.target.value })}
          />
          <TextArea
            label="Commentaire"
            value={form.comments}
            onChange={(e) => setForm({ ...form, comments: e.target.value })}
          />
        </form>
      </BottomSheet>
    </div>
  )
}
