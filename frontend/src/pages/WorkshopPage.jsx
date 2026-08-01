import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { api } from '../lib/api'
import { useAuth } from '../context/AuthContext'
import { useCoach } from '../components/Coach'
import { WORKSHOP_LABELS, WORKSHOP_ORDER } from '../lib/labels'
import {
  BottomSheet,
  Button,
  Card,
  ErrorBanner,
  PageHeader,
  PillSelector,
  Select,
  StatusPill,
} from '../components/ui'

export default function WorkshopPage() {
  const [board, setBoard] = useState(null)
  const [users, setUsers] = useState([])
  const [error, setError] = useState('')
  const [mine, setMine] = useState(false)
  const [selected, setSelected] = useState(null)
  const [assignId, setAssignId] = useState('')
  const [params, setParams] = useSearchParams()
  const focus = params.get('focus') || ''
  const navigate = useNavigate()
  const { user } = useAuth()
  const coach = useCoach()

  async function load(assigned = mine) {
    try {
      const data = await api(`/api/workshop/board${assigned ? '?assigned_to_me=true' : ''}`)
      setBoard(data)
    } catch (e) {
      setError(e.message)
    }
  }

  useEffect(() => {
    load()
    coach.show('workshop')
    api('/api/auth/users')
      .then(setUsers)
      .catch(() => setUsers([]))
  }, [mine])

  async function move(dossierId, status) {
    try {
      await api(`/api/workshop/dossiers/${dossierId}`, {
        method: 'PATCH',
        body: { workshop_status: status, note: '' },
      })
      setSelected(null)
      await load()
    } catch (e) {
      setError(e.message)
    }
  }

  async function assign(dossierId, status, userId) {
    try {
      await api(`/api/workshop/dossiers/${dossierId}`, {
        method: 'PATCH',
        body: {
          workshop_status: status,
          assigned_user_id: userId == null || userId === '' ? null : Number(userId),
        },
      })
      setSelected(null)
      await load()
    } catch (e) {
      setError(e.message)
    }
  }

  const order = board?.order || WORKSHOP_ORDER
  const flat = order.flatMap((s) => (board?.columns?.[s] || []).map((d) => ({ ...d })))
  const visible = focus ? flat.filter((d) => d.workshop_status === focus) : flat
  const userName = (id) => users.find((u) => u.id === id)?.full_name || (id ? `#${id}` : 'Non assigné')

  return (
    <div>
      <PageHeader
        title="Atelier"
        subtitle="Faites avancer les véhicules étape par étape"
        onHelp={() => coach.replay('workshop')}
        actions={
          <button
            type="button"
            onClick={() => setMine((v) => !v)}
            className={`rounded-[var(--radius-pill)] px-3 py-1.5 text-[12px] font-semibold ${
              mine ? 'bg-primary text-white' : 'bg-surface text-text-secondary'
            }`}
          >
            {mine ? 'Mes véhicules' : 'Tous'}
          </button>
        }
      />
      <ErrorBanner message={error} />

      <div className="mb-4">
        <PillSelector
          options={[
            { value: '', label: 'Tous' },
            ...order.map((s) => ({ value: s, label: WORKSHOP_LABELS[s] })),
          ]}
          value={focus}
          onChange={(v) => {
            if (v) params.set('focus', v)
            else params.delete('focus')
            setParams(params)
          }}
        />
      </div>

      <div className="space-y-2.5">
        {visible.map((d) => (
          <Card key={d.id} className="p-3.5">
            <button
              type="button"
              onClick={() => navigate(`/dossiers/${d.id}`)}
              className="flex w-full items-start justify-between gap-3 text-left"
            >
              <div className="min-w-0">
                <p className="truncate text-[15px] font-semibold text-text-primary">
                  {d.vehicle_make} {d.vehicle_model}
                </p>
                <p className="mt-0.5 truncate text-[12px] font-medium text-text-secondary">
                  {d.client_name} · {d.license_plate || d.reference}
                </p>
                <p className="mt-0.5 text-[11px] text-text-muted">{userName(d.assigned_user_id)}</p>
              </div>
              <StatusPill
                tone={
                  d.workshop_status === 'pret_a_livrer' || d.workshop_status === 'livre'
                    ? 'ok'
                    : 'info'
                }
              >
                {WORKSHOP_LABELS[d.workshop_status]}
              </StatusPill>
            </button>
            <div className="mt-3">
              <Button className="!min-h-[44px] !py-2.5 text-[13px]" fullWidth onClick={() => {
                setSelected(d)
                setAssignId(d.assigned_user_id ? String(d.assigned_user_id) : '')
              }}>
                Étape / Assigner
              </Button>
            </div>
          </Card>
        ))}
        {visible.length === 0 && (
          <p className="text-[13px] text-text-muted">Aucun véhicule dans cette vue.</p>
        )}
      </div>

      <BottomSheet
        open={!!selected}
        onClose={() => setSelected(null)}
        title="Étape atelier"
        footer={
          <Button variant="ghost" fullWidth onClick={() => setSelected(null)}>
            Fermer
          </Button>
        }
      >
        {selected && (
          <div className="space-y-3">
            <p className="text-[13px] text-text-secondary">
              {selected.vehicle_make} {selected.vehicle_model} — statut actuel :{' '}
              <strong>{WORKSHOP_LABELS[selected.workshop_status]}</strong>
            </p>
            <PillSelector
              options={order.map((s) => ({ value: s, label: WORKSHOP_LABELS[s] }))}
              value={selected.workshop_status}
              onChange={(status) => move(selected.id, status)}
            />
            <Select
              label="Assigné à"
              value={assignId}
              onChange={(e) => setAssignId(e.target.value)}
            >
              <option value="">Non assigné</option>
              {users.map((u) => (
                <option key={u.id} value={u.id}>
                  {u.full_name} {u.id === user?.id ? '(moi)' : ''}
                </option>
              ))}
            </Select>
            <Button
              fullWidth
              variant="outline"
              onClick={() => assign(selected.id, selected.workshop_status, assignId)}
            >
              Enregistrer l’assignation
            </Button>
          </div>
        )}
      </BottomSheet>
    </div>
  )
}
