import { useEffect, useRef, useState } from 'react'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import {
  api,
  authHeaders,
  apiUrl,
  downloadAuthenticatedFile,
  fetchAuthenticatedBlob,
} from '../lib/api'
import { compressImage } from '../lib/compressImage'
import { useCoach } from '../components/Coach'
import {
  EXTRACTION_LABELS,
  INVOICE_LABELS,
  OP_TYPES,
  QUOTE_LABELS,
  QUOTE_TONES,
  WORKSHOP_LABELS,
  WORKSHOP_TONES,
  money,
} from '../lib/labels'
import {
  Amount,
  BackButton,
  BottomSheet,
  Button,
  Card,
  ErrorBanner,
  Input,
  LoadingBlock,
  PageHeader,
  Select,
  StatusPill,
  StickyActions,
} from '../components/ui'

const tabs = ['Dossier', 'Devis', 'Facture', 'Historique']

function humanizeExtractionError(msg) {
  const raw = String(msg || '')
  if (!raw) return ''
  const lower = raw.toLowerCase()
  if (
    lower.includes('api.x.ai') ||
    lower.includes('403') ||
    lower.includes('permission-denied') ||
    lower.includes('credits') ||
    lower.includes('forbidden')
  ) {
    return (
      'Extraction IA indisponible : le compte Grok (xAI) n’a pas de crédits. ' +
      'Ajoutez des crédits sur console.x.ai, ou saisissez les opérations manuellement.'
    )
  }
  return raw
}

const TAB_MAP = {
  Dossier: 'dossier',
  Devis: 'devis',
  Facture: 'facture',
  Historique: 'historique',
}
const TAB_FROM_URL = Object.fromEntries(Object.entries(TAB_MAP).map(([k, v]) => [v, k]))

const fieldClass = '!bg-white ring-1 ring-border/80'

function opFieldGuide(type) {
  switch (type) {
    case 'piece_remplacer':
      return {
        descPlaceholder: 'Ex. Pare-chocs avant',
        showQty: true,
        showHours: false,
        showCost: true,
        qtyLabel: 'Quantité',
        qtyHint: 'Nombre de pièces',
        costLabel: 'Prix d’achat €',
        costHint: 'Prix fournisseur — la marge garage s’ajoute au devis',
      }
    case 'piece_reparer':
      return {
        descPlaceholder: 'Ex. Aile avant droite',
        showQty: true,
        showHours: true,
        showCost: true,
        qtyLabel: 'Quantité',
        qtyHint: 'Pièces / éléments',
        hoursLabel: 'Temps MO (h)',
        hoursHint: 'Heures de main d’œuvre (tarif garage)',
        costLabel: 'Prix pièce €',
        costHint: '0 si aucune pièce — sinon prix d’achat',
      }
    case 'peinture':
      return {
        descPlaceholder: 'Ex. Peinture pare-chocs',
        showQty: false,
        showHours: true,
        showCost: false,
        hoursLabel: 'Temps peinture (h)',
        hoursHint: 'Tarif horaire peinture du garage appliqué auto',
      }
    case 'main_doeuvre':
      return {
        descPlaceholder: 'Ex. Dépose / repose phare',
        showQty: false,
        showHours: true,
        showCost: false,
        hoursLabel: 'Temps (heures)',
        hoursHint: 'Tarif horaire carrosserie du garage appliqué auto',
      }
    case 'annexe':
      return {
        descPlaceholder: 'Ex. Forfait déplacement',
        showQty: true,
        showHours: false,
        showCost: true,
        qtyLabel: 'Quantité',
        costLabel: 'Montant unitaire €',
        costHint: 'Montant facturé tel quel',
      }
    default:
      return {
        descPlaceholder: 'Décrivez l’opération',
        showQty: true,
        showHours: true,
        showCost: true,
        qtyLabel: 'Quantité',
        hoursLabel: 'Heures',
        costLabel: 'Coût €',
      }
  }
}

function AuthImage({ path, alt }) {
  const [src, setSrc] = useState('')
  const [failed, setFailed] = useState(false)
  useEffect(() => {
    let url
    let cancelled = false
    fetchAuthenticatedBlob(path)
      .then((b) => {
        if (cancelled) return
        url = URL.createObjectURL(b)
        setSrc(url)
      })
      .catch(() => {
        if (!cancelled) setFailed(true)
      })
    return () => {
      cancelled = true
      if (url) URL.revokeObjectURL(url)
    }
  }, [path])
  if (failed) {
    return (
      <div className="flex aspect-video items-center justify-center rounded-[var(--radius-md)] bg-danger-bg text-[12px] font-medium text-danger">
        Photo indisponible
      </div>
    )
  }
  if (!src) return <div className="aspect-video animate-pulse rounded-[var(--radius-md)] bg-surface" />
  return (
    <img src={src} alt={alt} className="aspect-video w-full rounded-[var(--radius-md)] object-cover" />
  )
}

function StepPill({ n, label, done, current }) {
  return (
    <div
      className={`flex min-w-0 flex-1 flex-col items-center gap-1 rounded-[12px] px-2 py-2.5 text-center ${
        done ? 'bg-success-bg' : current ? 'bg-info-bg' : 'bg-surface'
      }`}
    >
      <span
        className={`flex h-6 w-6 items-center justify-center rounded-full text-[11px] font-bold ${
          done ? 'bg-success text-white' : current ? 'bg-primary text-white' : 'bg-border text-text-muted'
        }`}
      >
        {done ? '✓' : n}
      </span>
      <span
        className={`text-[10px] font-semibold leading-tight ${
          done ? 'text-success' : current ? 'text-primary' : 'text-text-muted'
        }`}
      >
        {label}
      </span>
    </div>
  )
}

function InfoRow({ label, value }) {
  if (!value) return null
  return (
    <div className="flex items-start justify-between gap-3 border-b border-border/60 py-2.5 last:border-0">
      <span className="shrink-0 text-[12px] font-medium text-text-muted">{label}</span>
      <span className="text-right text-[14px] font-semibold text-text-primary">{value}</span>
    </div>
  )
}

export default function DossierDetailPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const [dossier, setDossier] = useState(null)
  const [loading, setLoading] = useState(true)
  const tab = TAB_FROM_URL[searchParams.get('tab')] || 'Dossier'
  const [error, setError] = useState('')
  const [ops, setOps] = useState([])
  const [busy, setBusy] = useState(false)
  const [confirmQuote, setConfirmQuote] = useState(false)
  const [confirmInvoice, setConfirmInvoice] = useState(false)
  const uploadRef = useRef(null)
  const coach = useCoach()

  function setTab(next) {
    setSearchParams(
      (prev) => {
        const n = new URLSearchParams(prev)
        n.set('tab', TAB_MAP[next] || 'dossier')
        return n
      },
      { replace: true }
    )
  }

  async function load() {
    const d = await api(`/api/dossiers/${id}`)
    setDossier(d)
    setOps(d.expertise_report?.operations || [])
  }

  useEffect(() => {
    setLoading(true)
    setError('')
    load()
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [id])

  useEffect(() => {
    if (tab === 'Dossier') coach.show('expertise', { anchorEl: uploadRef.current })
    if (tab === 'Devis') coach.show('quote')
    if (tab === 'Facture') coach.show('invoice')
  }, [tab])

  async function uploadPhoto(e) {
    const file = e.target.files?.[0]
    if (!file) return
    setBusy(true)
    try {
      const compressed = await compressImage(file)
      const fd = new FormData()
      fd.append('file', compressed)
      const r = await fetch(apiUrl(`/api/dossiers/${id}/photos`), {
        method: 'POST',
        headers: authHeaders(),
        body: fd,
      })
      if (!r.ok) {
        let detail = 'Upload photo échoué'
        try {
          const data = await r.json()
          detail = typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail)
        } catch {
          /* ignore */
        }
        throw new Error(detail)
      }
      await load()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
      e.target.value = ''
    }
  }

  async function uploadExpertise(e) {
    const file = e.target.files?.[0]
    if (!file) return
    if (!file.name.toLowerCase().endsWith('.pdf') && file.type !== 'application/pdf') {
      setError('Le rapport d’expertise doit être un fichier PDF.')
      e.target.value = ''
      return
    }
    const fd = new FormData()
    fd.append('file', file)
    setBusy(true)
    setError('')
    try {
      const r = await fetch(apiUrl(`/api/dossiers/${id}/expertise`), {
        method: 'POST',
        headers: authHeaders(),
        body: fd,
      })
      if (!r.ok) {
        let detail = 'Échec de l’import du rapport d’expertise'
        try {
          const data = await r.json()
          detail = typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail)
        } catch {
          /* ignore */
        }
        throw new Error(detail)
      }
      await load()
      let done = false
      // ~15 s (19 × 800 ms)
      for (let i = 0; i < 19; i++) {
        await new Promise((res) => setTimeout(res, 800))
        const rep = await api(`/api/dossiers/${id}/expertise`)
        if (['draft', 'validated', 'failed'].includes(rep.status)) {
          setOps(rep.operations || [])
          await load()
          if (rep.status === 'failed') {
            setError(
              humanizeExtractionError(rep.error_message) ||
                'L’analyse du PDF a échoué. Réessayez avec un autre fichier ou ajoutez les lignes manuellement.'
            )
          } else if (rep.error_message) {
            setError(humanizeExtractionError(rep.error_message))
          } else {
            setError('')
          }
          done = true
          break
        }
      }
      if (!done) {
        setError(
          'L’analyse du rapport d’expertise dépasse le délai prévu. Veuillez actualiser la page dans quelques instants.'
        )
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
      e.target.value = ''
    }
  }

  function addEmptyOp() {
    setOps((prev) => [
      ...prev,
      {
        operation_type: 'main_doeuvre',
        description: '',
        quantity: 1,
        hours: 1,
        unit_cost: 0,
        labor_category: 'carrosserie',
      },
    ])
  }

  async function saveOps() {
    setBusy(true)
    try {
      await api(`/api/dossiers/${id}/expertise/operations`, { method: 'PUT', body: ops })
      await load()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  async function validateOps() {
    setBusy(true)
    try {
      await api(`/api/dossiers/${id}/expertise/operations`, { method: 'PUT', body: ops })
      await api(`/api/dossiers/${id}/expertise/validate`, { method: 'POST' })
      await load()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  async function generateQuote() {
    setBusy(true)
    try {
      await api(`/api/dossiers/${id}/quote`, { method: 'POST' })
      await load()
      setConfirmQuote(false)
      setTab('Devis')
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  async function setQuoteStatus(status) {
    if (!dossier.quote) return
    setBusy(true)
    try {
      await api(`/api/quotes/${dossier.quote.id}/status`, { method: 'PATCH', body: { status } })
      await load()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  async function createInvoice() {
    if (!dossier.quote) return
    setBusy(true)
    try {
      await api(`/api/quotes/${dossier.quote.id}/invoice`, { method: 'POST' })
      await load()
      setConfirmInvoice(false)
      setTab('Facture')
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  function downloadBlob(path, filename) {
    downloadAuthenticatedFile(path, filename).catch((e) => setError(e.message))
  }

  async function setClosed(is_closed) {
    setBusy(true)
    try {
      await api(`/api/dossiers/${id}`, { method: 'PATCH', body: { is_closed } })
      await load()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  async function markPaid(invoiceId) {
    setBusy(true)
    try {
      await api(`/api/invoices/${invoiceId}/status`, { method: 'PATCH', body: { status: 'payee' } })
      await load()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  async function emailQuote() {
    if (!dossier?.quote) return
    const to = window.prompt(
      'Adresse email du destinataire',
      dossier.client?.email || ''
    )
    if (!to) return
    setBusy(true)
    try {
      await api(`/api/quotes/${dossier.quote.id}/email`, { method: 'POST', body: { to } })
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  async function emailInvoice(invoiceId) {
    const to = window.prompt(
      'Adresse email du destinataire',
      dossier?.client?.email || ''
    )
    if (!to) return
    setBusy(true)
    try {
      await api(`/api/invoices/${invoiceId}/email`, { method: 'POST', body: { to } })
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  async function saveQuoteLines(quoteId, lines) {
    setBusy(true)
    try {
      await api(`/api/quotes/${quoteId}/lines`, {
        method: 'PUT',
        body: { lines },
      })
      await load()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  if (loading) return <LoadingBlock />
  if (!dossier) {
    return (
      <div>
        <BackButton onClick={() => navigate(-1)} />
        <ErrorBanner message={error || 'Dossier introuvable'} />
        <Button fullWidth onClick={() => navigate('/dossiers')}>
          Retour aux dossiers
        </Button>
      </div>
    )
  }

  const c = dossier.client
  const hasReport = Boolean(dossier.expertise_report)
  const hasOps = ops.length > 0
  const opsValidated = dossier.expertise_report?.status === 'validated'
  const hasQuote = Boolean(dossier.quote)
  const step = !hasOps ? 1 : !opsValidated ? 2 : !hasQuote ? 3 : 4

  const helpId = tab === 'Dossier' ? 'expertise' : tab === 'Devis' ? 'quote' : tab === 'Facture' ? 'invoice' : 'dossiers'

  return (
    <div>
      <BackButton onClick={() => navigate(-1)} />
      <PageHeader
        title={`${dossier.vehicle_make} ${dossier.vehicle_model}`.trim() || dossier.reference}
        subtitle={`${dossier.license_plate || 'Sans immat'} · ${dossier.reference}`}
        onHelp={() => coach.replay(helpId)}
        actions={
          <StatusPill tone={WORKSHOP_TONES[dossier.workshop_status]}>
            {WORKSHOP_LABELS[dossier.workshop_status]}
          </StatusPill>
        }
      />
      <div className="mb-3 flex flex-wrap gap-2">
        {dossier.is_closed ? (
          <Button
            variant="outline"
            className="!min-h-[40px] !px-3.5 text-[13px]"
            disabled={busy}
            onClick={() => setClosed(false)}
          >
            Réouvrir le dossier
          </Button>
        ) : (
          <Button
            variant="ghost"
            className="!min-h-[40px] !px-3.5 text-[13px]"
            disabled={busy}
            onClick={() => setClosed(true)}
          >
            Clôturer le dossier
          </Button>
        )}
        {dossier.is_closed ? (
          <StatusPill tone="neutral">Clôturé</StatusPill>
        ) : null}
      </div>
      <ErrorBanner message={error} />

      <div className="scroll-x -mx-4 mb-4 px-4">
        {tabs.map((t) => (
          <button
            key={t}
            type="button"
            onClick={() => setTab(t)}
            className={`min-h-[40px] rounded-[var(--radius-pill)] px-4 py-2.5 text-[13px] font-semibold ${
              tab === t ? 'bg-primary text-white' : 'bg-surface text-text-secondary'
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      {tab === 'Dossier' && (
        <div className="space-y-4 animate-pop">
          {/* Progress */}
          <div className="flex gap-2">
            <StepPill n={1} label="Infos" done current={step === 1} />
            <StepPill n={2} label="Expertise" done={hasOps} current={step === 2 || (hasOps && !opsValidated)} />
            <StepPill n={3} label="Valider" done={opsValidated} current={step === 3 || (hasOps && !opsValidated)} />
            <StepPill n={4} label="Devis" done={hasQuote} current={opsValidated && !hasQuote} />
          </div>

          {/* 1. Vehicle & client */}
          <Card className="overflow-hidden">
            <div className="bg-primary-dark px-4 py-3 text-white">
              <p className="text-[11px] font-semibold uppercase tracking-wide text-white/60">
                Véhicule
              </p>
              <p className="mt-0.5 text-[18px] font-bold">
                {dossier.vehicle_make} {dossier.vehicle_model}
                {dossier.vehicle_year ? ` · ${dossier.vehicle_year}` : ''}
              </p>
              <p className="mt-1 text-[14px] font-semibold text-primary">
                {dossier.license_plate || 'Immatriculation non renseignée'}
              </p>
            </div>
            <div className="px-4 py-1">
              <InfoRow label="Client" value={`${c.first_name} ${c.last_name}`.trim()} />
              <InfoRow label="Téléphone" value={c.phone} />
              <InfoRow label="Email" value={c.email} />
              <InfoRow label="VIN" value={dossier.vin} />
              <InfoRow label="Assurance" value={dossier.insurance_name} />
              <InfoRow label="N° sinistre" value={dossier.insurance_claim_number} />
              <InfoRow label="Référence" value={dossier.reference} />
            </div>
            {dossier.comments ? (
              <div className="border-t border-border px-4 py-3">
                <p className="text-[11px] font-semibold uppercase tracking-wide text-text-muted">
                  Commentaire
                </p>
                <p className="mt-1 text-[13px] leading-snug text-text-secondary">{dossier.comments}</p>
              </div>
            ) : null}
          </Card>

          {/* 2. Photos */}
          <Card className="p-4">
            <div className="mb-3 flex items-center justify-between gap-2">
              <div>
                <h2>Photos du véhicule</h2>
                <p className="mt-0.5 text-[12px] font-medium text-text-secondary">
                  Avant / après, dégâts, détail
                </p>
              </div>
              <label className="cursor-pointer">
                <span className="inline-flex min-h-[40px] items-center rounded-[var(--radius-pill)] bg-info-bg px-3.5 text-[13px] font-semibold text-primary">
                  + Photo
                </span>
                <input type="file" accept="image/*" capture="environment" className="hidden" onChange={uploadPhoto} />
              </label>
            </div>
            {dossier.photos.length === 0 ? (
              <label className="flex cursor-pointer flex-col items-center justify-center rounded-[var(--radius-md)] border-2 border-dashed border-border bg-surface px-4 py-8 text-center">
                <p className="text-[14px] font-semibold text-text-primary">Ajouter des photos</p>
                <p className="mt-1 text-[12px] text-text-muted">Galerie ou appareil photo</p>
                <input type="file" accept="image/*" capture="environment" className="hidden" onChange={uploadPhoto} />
              </label>
            ) : (
              <div className="grid grid-cols-2 gap-2">
                {dossier.photos.map((p) => (
                  <AuthImage
                    key={p.id}
                    path={`/api/dossiers/${id}/photos/${p.id}/file`}
                    alt={p.original_name}
                  />
                ))}
              </div>
            )}
          </Card>

          {/* 3. Expertise */}
          <Card className="p-4">
            <div className="mb-3 flex items-start justify-between gap-2">
              <div>
                <h2>Rapport d’expertise</h2>
                <p className="mt-0.5 text-[12px] font-medium text-text-secondary">
                  Importez un PDF ou saisissez les opérations
                </p>
              </div>
              {dossier.expertise_report && (
                <StatusPill
                  tone={
                    opsValidated ? 'ok' : dossier.expertise_report.status === 'failed' ? 'danger' : 'warn'
                  }
                >
                  {EXTRACTION_LABELS[dossier.expertise_report.status] || dossier.expertise_report.status}
                </StatusPill>
              )}
            </div>

            <label
              ref={uploadRef}
              className="mb-3 flex cursor-pointer flex-col items-center justify-center rounded-[var(--radius-md)] border-2 border-dashed border-primary/30 bg-info-bg/60 px-4 py-6 text-center"
            >
              <p className="text-[14px] font-semibold text-primary">
                {hasReport ? 'Remplacer le PDF' : 'Importer le PDF d’expertise'}
              </p>
              <p className="mt-1 text-[12px] font-medium text-text-secondary">
                Extraction auto des pièces et temps
              </p>
              <input type="file" accept="application/pdf" className="hidden" onChange={uploadExpertise} />
            </label>

            {busy && (
              <p className="mb-3 text-center text-[13px] font-medium text-text-secondary">
                Traitement en cours…
              </p>
            )}

            {ops.length > 0 ? (
              <div className="space-y-3">
                <p className="text-[12px] font-semibold uppercase tracking-wide text-text-muted">
                  Lignes d’opération ({ops.length})
                </p>
                {ops.map((op, idx) => {
                  const guide = opFieldGuide(op.operation_type)
                  const update = (patch) => {
                    const next = [...ops]
                    next[idx] = { ...op, ...patch }
                    setOps(next)
                  }
                  return (
                    <div
                      key={idx}
                      className="rounded-[var(--radius-md)] border border-border bg-surface p-3"
                    >
                      <div className="mb-2 flex items-center justify-between gap-2">
                        <p className="text-[12px] font-semibold text-text-secondary">
                          Ligne {idx + 1}
                        </p>
                        <button
                          type="button"
                          className="text-[12px] font-semibold text-danger"
                          onClick={() => setOps((prev) => prev.filter((_, i) => i !== idx))}
                        >
                          Supprimer
                        </button>
                      </div>
                      <Select
                        label="Type d’opération"
                        hint="Choisissez le type pour afficher les bons champs"
                        className={fieldClass}
                        value={op.operation_type}
                        onChange={(e) => update({ operation_type: e.target.value })}
                      >
                        {OP_TYPES.map((t) => (
                          <option key={t.value} value={t.value}>
                            {t.label}
                          </option>
                        ))}
                      </Select>
                      <div className="mt-2">
                        <Input
                          label="Libellé"
                          placeholder={guide.descPlaceholder}
                          className={fieldClass}
                          value={op.description}
                          onChange={(e) => update({ description: e.target.value })}
                        />
                      </div>
                      <div className="mt-2 grid grid-cols-2 gap-2">
                        {guide.showQty ? (
                          <Input
                            label={guide.qtyLabel}
                            hint={guide.qtyHint}
                            type="number"
                            inputMode="decimal"
                            step="1"
                            min="0"
                            placeholder="1"
                            className={fieldClass}
                            value={op.quantity}
                            onChange={(e) => update({ quantity: Number(e.target.value) })}
                          />
                        ) : null}
                        {guide.showHours ? (
                          <Input
                            label={guide.hoursLabel}
                            hint={guide.hoursHint}
                            type="number"
                            inputMode="decimal"
                            step="0.1"
                            min="0"
                            placeholder="ex. 1,5"
                            className={fieldClass}
                            value={op.hours}
                            onChange={(e) => update({ hours: Number(e.target.value) })}
                          />
                        ) : null}
                        {guide.showCost ? (
                          <Input
                            label={guide.costLabel}
                            hint={guide.costHint}
                            type="number"
                            inputMode="decimal"
                            step="0.01"
                            min="0"
                            placeholder="ex. 120"
                            className={fieldClass}
                            value={op.unit_cost}
                            onChange={(e) => update({ unit_cost: Number(e.target.value) })}
                          />
                        ) : null}
                      </div>
                    </div>
                  )
                })}
              </div>
            ) : (
              <div className="rounded-[var(--radius-sm)] bg-surface px-3 py-4 text-center">
                <p className="text-[13px] font-semibold text-text-primary">Aucune opération</p>
                <p className="mt-1 text-[12px] text-text-secondary">
                  Importez le PDF expert ci-dessus, ou ajoutez une ligne à la main.
                </p>
              </div>
            )}

            <Button
              variant="ghost"
              fullWidth
              className="mt-3 !min-h-[44px] text-[13px]"
              onClick={addEmptyOp}
            >
              + Ajouter une opération
            </Button>
          </Card>

          {/* Guide d’étapes — déroulé jusqu’en bas, puis les actions */}
          <Card className="border border-primary/15 bg-info-bg/40 p-4">
            <p className="text-[12px] font-semibold uppercase tracking-wide text-primary">
              Parcours devis
            </p>
            <p className="mt-1 text-[14px] font-semibold text-text-primary">
              De l’expertise au devis, en 4 étapes
            </p>
            <p className="mt-1 text-[13px] leading-snug text-text-secondary">
              Faites défiler jusqu’en bas : l’action à lancer se trouve sous ce guide.
            </p>

            <ol className="mt-4 space-y-3">
              {[
                {
                  n: 1,
                  done: hasOps,
                  current: !hasOps,
                  title: 'Remplir les opérations',
                  detail:
                    'Importez le PDF d’expertise (zone bleue plus haut) pour extraire pièces et temps, ou ajoutez une ligne manuellement avec « + Ajouter une opération ».',
                  tip: 'Sans au moins une opération, le devis ne peut pas être calculé.',
                },
                {
                  n: 2,
                  done: hasOps && ops.every((o) => (o.description || '').trim()),
                  current: hasOps && !opsValidated && !ops.every((o) => (o.description || '').trim()),
                  title: 'Compléter chaque ligne',
                  detail:
                    'Pour chaque opération : libellé clair, puis quantité / heures / prix selon le type (pièce, main d’œuvre, peinture…).',
                  tip: 'Les champs s’adaptent au type choisi — vérifiez avant de valider.',
                },
                {
                  n: 3,
                  done: opsValidated,
                  current: hasOps && !opsValidated && ops.every((o) => (o.description || '').trim()),
                  title: 'Valider l’expertise',
                  detail:
                    'Quand les lignes sont correctes, validez l’expertise. Cela fige les opérations et autorise le chiffrage.',
                  tip: 'Vous pourrez encore régénérer un devis tant qu’aucune facture n’existe.',
                },
                {
                  n: 4,
                  done: hasQuote,
                  current: opsValidated && !hasQuote,
                  title: 'Générer le devis',
                  detail:
                    'Les tarifs du garage (MO, peinture, marges, TVA) sont appliqués automatiquement. Le PDF est prêt à envoyer ou accepter.',
                  tip: 'Ensuite : onglet Devis → accepter → facturer.',
                },
              ].map((s) => (
                <li
                  key={s.n}
                  className={`rounded-[var(--radius-md)] px-3 py-3 ${
                    s.current
                      ? 'bg-white ring-2 ring-primary/30'
                      : s.done
                        ? 'bg-white/50'
                        : 'bg-white/70 ring-1 ring-border/60'
                  }`}
                >
                  <div className="flex gap-3">
                    <span
                      className={`mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-[13px] font-bold ${
                        s.done
                          ? 'bg-success text-white'
                          : s.current
                            ? 'bg-primary text-white'
                            : 'bg-surface text-text-muted ring-1 ring-border'
                      }`}
                    >
                      {s.done ? '✓' : s.n}
                    </span>
                    <div className="min-w-0 flex-1">
                      <p
                        className={`text-[14px] font-semibold ${
                          s.done ? 'text-text-muted line-through' : 'text-text-primary'
                        }`}
                      >
                        {s.title}
                        {s.current ? (
                          <span className="ml-2 text-[11px] font-bold uppercase tracking-wide text-primary">
                            En cours
                          </span>
                        ) : null}
                      </p>
                      <p className="mt-1 text-[12px] leading-relaxed text-text-secondary">{s.detail}</p>
                      {s.current || (!s.done && s.n === step) ? (
                        <p className="mt-2 text-[11px] font-medium leading-snug text-primary">{s.tip}</p>
                      ) : (
                        <p className="mt-1.5 text-[11px] leading-snug text-text-muted">{s.tip}</p>
                      )}
                    </div>
                  </div>
                </li>
              ))}
            </ol>

            <div className="mt-4 rounded-[var(--radius-md)] bg-primary px-3.5 py-3 text-white">
              <p className="text-[11px] font-semibold uppercase tracking-wide text-white/80">
                À faire maintenant
              </p>
              <p className="mt-1 text-[14px] font-semibold leading-snug">
                {!hasOps && 'Importez le PDF ou saisissez une opération (boutons juste en dessous).'}
                {hasOps && !opsValidated && 'Vérifiez les lignes, puis validez l’expertise.'}
                {opsValidated && !hasQuote && 'Générez le devis avec les tarifs du garage.'}
                {hasQuote && 'Consultez le devis dans l’onglet Devis.'}
              </p>
              <p className="mt-2 text-[11px] text-white/70">↓ Continuez vers le bas</p>
            </div>
          </Card>

          <StickyActions sticky={false}>
            {hasOps && !opsValidated && (
              <>
                <Button variant="outline" fullWidth onClick={saveOps} disabled={busy}>
                  Enregistrer les corrections
                </Button>
                <Button fullWidth onClick={validateOps} disabled={busy || ops.length === 0}>
                  Valider l’expertise
                </Button>
              </>
            )}
            {opsValidated && !hasQuote && (
              <Button fullWidth onClick={() => setConfirmQuote(true)} disabled={busy}>
                Générer le devis
              </Button>
            )}
            {hasQuote && (
              <Button fullWidth onClick={() => setTab('Devis')}>
                Voir le devis →
              </Button>
            )}
            {!hasOps && (
              <>
                <Button
                  fullWidth
                  onClick={() =>
                    uploadRef.current?.click?.() ||
                    document.querySelector('input[accept="application/pdf"]')?.click()
                  }
                >
                  1. Importer le PDF d’expertise
                </Button>
                <Button variant="outline" fullWidth onClick={addEmptyOp}>
                  Ou saisir une opération à la main
                </Button>
              </>
            )}
          </StickyActions>
        </div>
      )}

      {tab === 'Devis' && (
        <QuotePanel
          dossier={dossier}
          busy={busy}
          onStatus={setQuoteStatus}
          onGenerate={() => setConfirmQuote(true)}
          onDownload={downloadBlob}
          onInvoice={() => setConfirmInvoice(true)}
          onEmail={emailQuote}
          onSaveLines={saveQuoteLines}
        />
      )}

      {tab === 'Facture' && (
        <InvoicePanel
          dossier={dossier}
          busy={busy}
          onCreate={() => setConfirmInvoice(true)}
          onDownload={downloadBlob}
          onMarkPaid={markPaid}
          onEmail={emailInvoice}
        />
      )}

      {tab === 'Historique' && (
        <div className="space-y-4 animate-pop">
          <Card className="space-y-3 p-4">
            <h2>Statuts atelier</h2>
            {dossier.status_history.length === 0 ? (
              <p className="text-[13px] text-text-muted">Aucun changement de statut.</p>
            ) : (
              dossier.status_history.map((h) => (
                <div key={h.id} className="border-l-2 border-primary pl-3">
                  <p className="text-[12px] font-medium text-text-muted">
                    {new Date(h.created_at).toLocaleString('fr-FR')}
                  </p>
                  <p className="text-[13px]">
                    {WORKSHOP_LABELS[h.from_status] || '—'} →{' '}
                    {WORKSHOP_LABELS[h.to_status] || h.to_status}
                  </p>
                </div>
              ))
            )}
          </Card>
          <Card className="space-y-3 p-4">
            <h2>Modifications</h2>
            {dossier.audit_logs.length === 0 ? (
              <p className="text-[13px] text-text-muted">Aucune modification enregistrée.</p>
            ) : (
              dossier.audit_logs.map((a) => (
                <div key={a.id}>
                  <p className="text-[12px] font-medium text-text-muted">
                    {new Date(a.created_at).toLocaleString('fr-FR')}
                  </p>
                  <p className="text-[13px]">
                    <span className="font-semibold">{a.action}</span> {a.details}
                  </p>
                </div>
              ))
            )}
          </Card>
        </div>
      )}

      <BottomSheet
        open={confirmQuote}
        onClose={() => setConfirmQuote(false)}
        title="Générer le devis"
        footer={
          <>
            <Button fullWidth onClick={generateQuote} disabled={busy}>
              Confirmer la génération
            </Button>
            <Button variant="ghost" fullWidth onClick={() => setConfirmQuote(false)}>
              Annuler
            </Button>
          </>
        }
      >
        <p className="text-[14px] text-text-secondary">
          Les opérations validées seront chiffrées avec les tarifs du garage (MO, peinture, marges,
          TVA).
        </p>
      </BottomSheet>

      <BottomSheet
        open={confirmInvoice}
        onClose={() => setConfirmInvoice(false)}
        title="Transformer en facture"
        footer={
          <>
            <Button fullWidth onClick={createInvoice} disabled={busy}>
              Créer la facture
            </Button>
            <Button variant="ghost" fullWidth onClick={() => setConfirmInvoice(false)}>
              Annuler
            </Button>
          </>
        }
      >
        <p className="text-[14px] text-text-secondary">
          Le devis accepté sera figé en facture PDF, sans ressaisie des lignes.
        </p>
      </BottomSheet>
    </div>
  )
}

function QuotePanel({
  dossier,
  busy,
  onStatus,
  onGenerate,
  onDownload,
  onInvoice,
  onEmail,
  onSaveLines,
}) {
  const q = dossier.quote
  const editable = q && ['brouillon', 'en_attente'].includes(q.status)
  const [lines, setLines] = useState([])
  const history = (dossier.quotes || [])
    .slice()
    .sort((a, b) => (b.version || 0) - (a.version || 0))

  useEffect(() => {
    if (!q) {
      setLines([])
      return
    }
    setLines(
      (q.lines || []).map((l) => ({
        id: l.id,
        category: l.category || 'annexe',
        description: l.description || '',
        quantity: l.quantity ?? 1,
        unit_price: l.unit_price ?? 0,
        sort_order: l.sort_order ?? 0,
        total: l.total,
      }))
    )
  }, [q?.id, q?.updated_at, q?.status])

  if (!q) {
    return (
      <div className="space-y-3 animate-pop">
        <p className="text-[13px] text-text-secondary">
          Pas encore de devis. Validez l’expertise dans l’onglet Dossier.
        </p>
        <Button fullWidth onClick={onGenerate} disabled={busy}>
          Générer le devis
        </Button>
      </div>
    )
  }

  function updateLine(idx, patch) {
    setLines((prev) => {
      const next = [...prev]
      next[idx] = { ...next[idx], ...patch }
      return next
    })
  }

  return (
    <div className="space-y-4 animate-pop">
      <Card className="p-4">
        <div className="flex items-center justify-between gap-2">
          <div>
            <p className="text-[17px] font-semibold">{q.number}</p>
            <p className="mt-0.5 text-[12px] font-medium text-text-muted">
              Version {q.version || 1}
            </p>
          </div>
          <StatusPill tone={QUOTE_TONES[q.status]}>{QUOTE_LABELS[q.status]}</StatusPill>
        </div>
        <div className="mt-4 space-y-2">
          {editable
            ? lines.map((l, idx) => (
                <div
                  key={l.id ?? idx}
                  className="rounded-[var(--radius-sm)] border border-border bg-surface p-2.5"
                >
                  <Input
                    label="Libellé"
                    className={fieldClass}
                    value={l.description}
                    onChange={(e) => updateLine(idx, { description: e.target.value })}
                  />
                  <div className="mt-2 grid grid-cols-2 gap-2">
                    <Input
                      label="Quantité"
                      type="number"
                      inputMode="decimal"
                      step="0.1"
                      min="0"
                      className={fieldClass}
                      value={l.quantity}
                      onChange={(e) => updateLine(idx, { quantity: Number(e.target.value) })}
                    />
                    <Input
                      label="Prix unitaire €"
                      type="number"
                      inputMode="decimal"
                      step="0.01"
                      min="0"
                      className={fieldClass}
                      value={l.unit_price}
                      onChange={(e) => updateLine(idx, { unit_price: Number(e.target.value) })}
                    />
                  </div>
                </div>
              ))
            : q.lines.map((l) => (
                <div key={l.id} className="flex justify-between gap-3 text-[13px]">
                  <span className="text-text-secondary">{l.description}</span>
                  <Amount value={money(l.total)} />
                </div>
              ))}
        </div>
        <div className="mt-4 border-t border-border pt-3">
          <div className="flex justify-between text-[13px] text-text-secondary">
            <span>HT</span>
            <Amount value={money(q.total_ht)} />
          </div>
          <div className="mt-1 flex justify-between text-[13px] text-text-secondary">
            <span>TVA</span>
            <Amount value={money(q.tva_amount)} />
          </div>
          <div className="mt-2 flex justify-between text-[18px]">
            <span className="font-semibold">TTC</span>
            <Amount value={money(q.total_ttc)} highlight className="text-[22px]" />
          </div>
        </div>
      </Card>

      {history.length > 1 ? (
        <Card className="space-y-2 p-4">
          <h2>Historique des versions</h2>
          {history.map((h) => (
            <div
              key={h.id}
              className="flex items-center justify-between gap-2 border-b border-border/60 py-2 last:border-0"
            >
              <div>
                <p className="text-[13px] font-semibold text-text-primary">
                  {h.number} · v{h.version}
                </p>
                <p className="text-[11px] text-text-muted">
                  {QUOTE_LABELS[h.status] || h.status}
                  {h.id === q.id ? ' · actuelle' : ''}
                </p>
              </div>
              <Amount value={money(h.total_ttc)} />
            </div>
          ))}
        </Card>
      ) : null}

      <StickyActions>
        {editable ? (
          <Button
            fullWidth
            variant="outline"
            disabled={busy}
            onClick={() =>
              onSaveLines(
                q.id,
                lines.map((l, i) => ({
                  id: l.id,
                  category: l.category || 'annexe',
                  description: l.description,
                  quantity: l.quantity,
                  unit_price: l.unit_price,
                  sort_order: l.sort_order ?? i,
                }))
              )
            }
          >
            Enregistrer les lignes
          </Button>
        ) : null}
        <div className="grid grid-cols-2 gap-2">
          <Button variant="outline" onClick={() => onStatus('en_attente')} disabled={busy}>
            En attente
          </Button>
          <Button onClick={() => onStatus('accepte')} disabled={busy}>
            Accepter
          </Button>
        </div>
        <Button variant="ghost" fullWidth onClick={onEmail} disabled={busy}>
          Envoyer par email
        </Button>
        <Button
          variant="ghost"
          fullWidth
          onClick={() => onDownload(`/api/quotes/${q.id}/pdf`, `${q.number}.pdf`)}
        >
          Télécharger PDF
        </Button>
        {q.status === 'accepte' && (
          <Button fullWidth onClick={onInvoice} disabled={busy}>
            Transformer en facture
          </Button>
        )}
      </StickyActions>
    </div>
  )
}

function InvoicePanel({ dossier, busy, onCreate, onDownload, onMarkPaid, onEmail }) {
  const [invoice, setInvoice] = useState(null)

  useEffect(() => {
    api(`/api/dossiers/${dossier.id}/invoice`)
      .then(setInvoice)
      .catch(() => setInvoice(null))
  }, [dossier.id, dossier.quote?.status, dossier.is_closed, dossier.updated_at])

  if (!invoice) {
    return (
      <div className="space-y-3 animate-pop">
        <p className="text-[13px] text-text-secondary">
          Acceptez d’abord le devis, puis créez la facture.
        </p>
        <Button fullWidth onClick={onCreate} disabled={busy || dossier.quote?.status !== 'accepte'}>
          Créer la facture
        </Button>
      </div>
    )
  }

  return (
    <div className="space-y-4 animate-pop">
      <Card className="space-y-3 p-4">
        <div className="flex items-center justify-between gap-2">
          <p className="text-[17px] font-semibold">{invoice.number}</p>
          <StatusPill tone={invoice.status === 'payee' ? 'ok' : 'warn'}>
            {INVOICE_LABELS[invoice.status] || invoice.status}
          </StatusPill>
        </div>
        <div className="flex justify-between text-[18px]">
          <span className="font-semibold">TTC</span>
          <Amount value={money(invoice.total_ttc)} highlight className="text-[22px]" />
        </div>
      </Card>
      <StickyActions>
        {invoice.status !== 'payee' ? (
          <Button fullWidth onClick={() => onMarkPaid(invoice.id)} disabled={busy}>
            Marquer comme payée
          </Button>
        ) : null}
        <Button variant="ghost" fullWidth onClick={() => onEmail(invoice.id)} disabled={busy}>
          Envoyer par email
        </Button>
        <Button
          fullWidth
          variant="outline"
          onClick={() => onDownload(`/api/invoices/${invoice.id}/pdf`, `${invoice.number}.pdf`)}
        >
          Télécharger PDF
        </Button>
      </StickyActions>
    </div>
  )
}
