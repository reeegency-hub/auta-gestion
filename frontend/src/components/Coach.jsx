import { createContext, useCallback, useContext, useMemo, useState } from 'react'
import { createPortal } from 'react-dom'

const CoachContext = createContext(null)

const STORAGE_KEY = 'auta_coachmarks_seen'

function loadSeen() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}')
  } catch {
    return {}
  }
}

export const COACH_COPY = {
  dashboard: {
    title: 'Tableau de bord',
    body: 'Suivez l’activité en un coup d’œil. Touchez un compteur pour filtrer dossiers, devis ou atelier.',
  },
  dossiers: {
    title: 'Dossiers',
    body: 'Créez un dossier client rapidement, puis ajoutez photos et rapport d’expertise.',
  },
  expertise: {
    title: 'Import rapport',
    body: 'Déposez le PDF d’expertise ici : les pièces et temps sont extraits automatiquement.',
  },
  quote: {
    title: 'Générer un devis',
    body: 'Après validation des opérations, générez le devis avec les tarifs du garage.',
  },
  workshop: {
    title: 'Atelier',
    body: 'Faites avancer un véhicule d’étape en étape pour suivre la production en temps réel.',
  },
  invoice: {
    title: 'Facturation',
    body: 'Un devis accepté se transforme en facture sans ressaisie.',
  },
}

export function CoachProvider({ children }) {
  const [seen, setSeen] = useState(loadSeen)
  const [active, setActive] = useState(null)
  const [anchor, setAnchor] = useState(null)

  const markSeen = useCallback((id) => {
    setSeen((prev) => {
      const next = { ...prev, [id]: true }
      localStorage.setItem(STORAGE_KEY, JSON.stringify(next))
      return next
    })
  }, [])

  const show = useCallback(
    (id, { force = false, anchorEl = null } = {}) => {
      if (!COACH_COPY[id]) return
      if (!force && seen[id]) return
      // Never stack: if another coach is visible, skip auto-show
      if (!force && active) return
      setAnchor(anchorEl)
      setActive(id)
    },
    [seen, active]
  )

  const hide = useCallback(() => {
    if (active) markSeen(active)
    setActive(null)
    setAnchor(null)
  }, [active, markSeen])

  const dismissAll = useCallback(() => {
    const next = { ...seen }
    Object.keys(COACH_COPY).forEach((k) => {
      next[k] = true
    })
    localStorage.setItem(STORAGE_KEY, JSON.stringify(next))
    setSeen(next)
    setActive(null)
    setAnchor(null)
  }, [seen])

  const replay = useCallback(
    (id) => {
      show(id, { force: true })
    },
    [show]
  )

  const value = useMemo(
    () => ({ show, hide, replay, dismissAll, seen, active }),
    [show, hide, replay, dismissAll, seen, active]
  )

  return (
    <CoachContext.Provider value={value}>
      {children}
      {active && COACH_COPY[active] ? (
        <CoachBubble copy={COACH_COPY[active]} onDismiss={hide} onDismissAll={dismissAll} />
      ) : null}
    </CoachContext.Provider>
  )
}

export function useCoach() {
  return useContext(CoachContext)
}

function CoachBubble({ copy, onDismiss, onDismissAll }) {
  return createPortal(
    <div className="pointer-events-none fixed inset-0 z-[60]">
      <button
        type="button"
        className="pointer-events-auto absolute inset-0 bg-primary-dark/25 animate-fade"
        aria-label="Fermer l’aide"
        onClick={onDismiss}
      />
      <div className="pointer-events-auto absolute inset-x-4 bottom-[calc(100px+env(safe-area-inset-bottom))] animate-pop rounded-[var(--radius-md)] bg-primary-dark p-4 text-white card-shadow sm:inset-x-auto sm:left-1/2 sm:w-full sm:max-w-[400px] sm:-translate-x-1/2">
        <p className="text-[15px] font-semibold">{copy.title}</p>
        <p className="mt-1.5 text-[13px] font-medium leading-snug text-white/80">{copy.body}</p>
        <button
          type="button"
          onClick={onDismiss}
          className="mt-3 min-h-[44px] w-full rounded-[var(--radius-sm)] bg-primary px-3 py-2.5 text-[13px] font-semibold text-white"
        >
          Compris
        </button>
        <button
          type="button"
          onClick={onDismissAll}
          className="mt-2 w-full py-2 text-[12px] font-medium text-white/70"
        >
          Ne plus afficher l’aide
        </button>
      </div>
    </div>,
    document.body
  )
}
