import { createPortal } from 'react-dom'
import { useEffect, useState } from 'react'

export function PageHeader({ title, subtitle, actions, onHelp }) {
  return (
    <div className="mb-4 flex items-start justify-between gap-3">
      <div className="min-w-0 flex-1 animate-pop">
        <h1 className="pr-2">{title}</h1>
        {subtitle ? (
          <p className="mt-1 text-[13px] font-medium leading-snug text-text-secondary">{subtitle}</p>
        ) : null}
      </div>
      <div className="flex shrink-0 items-center gap-2 pt-0.5">
        {actions}
        {onHelp ? (
          <button
            type="button"
            onClick={onHelp}
            aria-label="Aide"
            className="flex h-10 w-10 items-center justify-center rounded-full bg-surface text-[15px] font-semibold text-text-secondary active:bg-info-bg active:text-primary"
          >
            ?
          </button>
        ) : null}
      </div>
    </div>
  )
}

export function Button({
  children,
  variant = 'primary',
  className = '',
  type = 'button',
  fullWidth = false,
  ...props
}) {
  const styles = {
    primary: 'bg-primary text-white active:brightness-95',
    secondary: 'bg-primary-dark text-white active:brightness-110',
    outline: 'bg-white text-text-primary border border-border active:bg-surface',
    ghost: 'bg-surface text-text-secondary active:text-text-primary',
    danger: 'bg-danger text-white active:brightness-95',
  }
  return (
    <button
      type={type}
      className={`min-h-[48px] rounded-[var(--radius-md)] px-4 py-3.5 text-[15px] font-semibold transition disabled:opacity-50 ${
        fullWidth ? 'w-full' : ''
      } ${styles[variant]} ${className}`}
      {...props}
    >
      {children}
    </button>
  )
}

export function Input({ label, hint, className = '', selectOnFocus, onFocus, ...props }) {
  const shouldSelect = selectOnFocus ?? props.type === 'number'
  return (
    <label className="block">
      {label ? (
        <span className="mb-1.5 block text-[12px] font-medium text-text-secondary">{label}</span>
      ) : null}
      <input
        className={`min-h-[48px] w-full rounded-[var(--radius-sm)] border-0 bg-surface px-3.5 py-3 text-text-primary outline-none ring-primary/25 placeholder:text-text-muted focus:ring-2 ${className}`}
        onFocus={(e) => {
          if (shouldSelect) e.target.select()
          onFocus?.(e)
        }}
        {...props}
      />
      {hint ? <span className="mt-1 block text-[11px] leading-snug text-text-muted">{hint}</span> : null}
    </label>
  )
}

export function SearchInput({ value, onChange, placeholder = 'Rechercher…', onSubmit }) {
  return (
    <form
      className="relative"
      onSubmit={(e) => {
        e.preventDefault()
        onSubmit?.(value)
      }}
    >
      <span className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-text-muted">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <circle cx="11" cy="11" r="7" />
          <path d="M20 20l-3-3" />
        </svg>
      </span>
      <input
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        enterKeyHint="search"
        className="min-h-[48px] w-full rounded-[var(--radius-sm)] border-0 bg-surface py-3 pl-11 pr-3 outline-none ring-primary/25 placeholder:text-text-muted focus:ring-2"
      />
    </form>
  )
}

export function Select({ label, hint, className = '', children, ...props }) {
  return (
    <label className="block">
      {label ? (
        <span className="mb-1.5 block text-[12px] font-medium text-text-secondary">{label}</span>
      ) : null}
      <select
        className={`min-h-[48px] w-full appearance-none rounded-[var(--radius-sm)] border-0 bg-surface px-3.5 py-3 outline-none ring-primary/25 focus:ring-2 ${className}`}
        {...props}
      >
        {children}
      </select>
      {hint ? <span className="mt-1 block text-[11px] leading-snug text-text-muted">{hint}</span> : null}
    </label>
  )
}

export function TextArea({ label, ...props }) {
  return (
    <label className="block">
      {label ? (
        <span className="mb-1.5 block text-[12px] font-medium text-text-secondary">{label}</span>
      ) : null}
      <textarea
        className="w-full rounded-[var(--radius-sm)] border-0 bg-surface px-3.5 py-3 outline-none ring-primary/25 focus:ring-2"
        rows={3}
        {...props}
      />
    </label>
  )
}

export function Card({ children, className = '', onClick }) {
  const Comp = onClick ? 'button' : 'div'
  return (
    <Comp
      type={onClick ? 'button' : undefined}
      onClick={onClick}
      className={`card-shadow w-full rounded-[var(--radius-md)] bg-white text-left ${className}`}
    >
      {children}
    </Comp>
  )
}

export function EmptyState({ title, text }) {
  return (
    <div className="rounded-[var(--radius-md)] bg-surface px-5 py-10 text-center">
      <p className="text-[16px] font-semibold text-text-primary">{title}</p>
      <p className="mt-2 text-[13px] font-medium leading-snug text-text-secondary">{text}</p>
    </div>
  )
}

export function StatusPill({ children, tone = 'neutral' }) {
  const tones = {
    neutral: 'bg-info-bg text-primary',
    info: 'bg-info-bg text-primary',
    warn: 'bg-warning-bg text-warning',
    ok: 'bg-success-bg text-success',
    danger: 'bg-danger-bg text-danger',
  }
  return (
    <span
      className={`inline-flex max-w-[140px] items-center truncate rounded-[var(--radius-pill)] px-2.5 py-1 text-[11px] font-semibold ${tones[tone] || tones.neutral}`}
    >
      {children}
    </span>
  )
}

export function PillSelector({ options, value, onChange }) {
  return (
    <div className="scroll-x -mx-4 px-4">
      {options.map((opt) => {
        const active = value === opt.value
        return (
          <button
            key={opt.value}
            type="button"
            onClick={() => onChange(opt.value)}
            className={`min-h-[40px] rounded-[var(--radius-pill)] px-4 py-2.5 text-[13px] font-semibold transition ${
              active
                ? 'bg-primary text-white'
                : 'bg-surface text-text-secondary active:text-text-primary'
            }`}
          >
            {opt.label}
          </button>
        )
      })}
    </div>
  )
}

export function ErrorBanner({ message }) {
  if (!message) return null
  return (
    <div className="mb-4 rounded-[var(--radius-sm)] bg-danger-bg px-4 py-3 text-[13px] font-medium leading-snug text-danger">
      {message}
    </div>
  )
}

export function BottomSheet({ open, onClose, title, children, footer }) {
  const [kbPad, setKbPad] = useState(0)

  useEffect(() => {
    if (!open) return undefined
    const vv = window.visualViewport
    if (!vv) return undefined
    const sync = () => {
      const covered = Math.max(0, window.innerHeight - vv.height - vv.offsetTop)
      setKbPad(covered)
    }
    sync()
    vv.addEventListener('resize', sync)
    vv.addEventListener('scroll', sync)
    return () => {
      vv.removeEventListener('resize', sync)
      vv.removeEventListener('scroll', sync)
    }
  }, [open])

  useEffect(() => {
    if (!open) return undefined
    const prev = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      document.body.style.overflow = prev
    }
  }, [open])

  if (!open) return null
  return createPortal(
    <div className="fixed inset-0 z-50 flex items-end justify-center">
      <button
        type="button"
        aria-label="Fermer"
        className="absolute inset-0 bg-primary-dark/45 animate-fade"
        onClick={onClose}
      />
      <div
        className="sheet-shadow animate-sheet relative z-10 flex w-full max-w-[430px] flex-col rounded-t-[var(--radius-lg)] bg-white px-4 pt-3"
        style={{
          maxHeight: `min(88dvh, calc(100dvh - ${kbPad}px - 8px))`,
          paddingBottom: kbPad > 0 ? 8 : undefined,
        }}
      >
        <div className="mx-auto mb-3 h-1 w-10 rounded-full bg-border" />
        {title ? <h2 className="mb-3 px-1">{title}</h2> : null}
        <div
          className="min-h-0 flex-1 overflow-y-auto overscroll-contain px-1 pb-2"
          onFocusCapture={(e) => {
            const el = e.target
            if (el?.scrollIntoView) {
              setTimeout(() => el.scrollIntoView({ block: 'center', behavior: 'smooth' }), 120)
            }
          }}
        >
          {children}
        </div>
        {footer ? (
          <div className="safe-bottom space-y-2 border-t border-border/60 bg-white px-1 pt-3">
            {footer}
          </div>
        ) : (
          <div className="safe-bottom" />
        )}
      </div>
    </div>,
    document.body
  )
}

export function Amount({ value, highlight = false, className = '' }) {
  return (
    <span
      className={`font-bold tabular-nums ${highlight ? 'text-primary' : 'text-text-primary'} ${className}`}
    >
      {value}
    </span>
  )
}

export function StickyActions({ children, sticky = true }) {
  if (!sticky) {
    return (
      <div className="-mx-4 mt-2 border-t border-border/70 bg-white px-4 py-4">
        <div className="space-y-2">{children}</div>
      </div>
    )
  }
  return (
    <div className="sticky bottom-[calc(var(--nav-h,72px)+env(safe-area-inset-bottom))] z-20 -mx-4 mt-4 border-t border-border/70 bg-white/95 px-4 py-3 backdrop-blur-md">
      <div className="space-y-2">{children}</div>
    </div>
  )
}

export function LoadingBlock({ label = 'Chargement…' }) {
  return (
    <div className="flex items-center justify-center py-16 text-[13px] font-medium text-text-secondary">
      {label}
    </div>
  )
}

export function BackButton({ onClick }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="mb-2 flex h-10 items-center gap-1 text-[13px] font-semibold text-primary"
    >
      ← Retour
    </button>
  )
}
