import { useEffect, useState } from 'react'

/** Bannière globale hors-ligne. */
export default function OfflineBanner() {
  const [offline, setOffline] = useState(typeof navigator !== 'undefined' ? !navigator.onLine : false)

  useEffect(() => {
    const goOff = () => setOffline(true)
    const goOn = () => setOffline(false)
    window.addEventListener('offline', goOff)
    window.addEventListener('online', goOn)
    return () => {
      window.removeEventListener('offline', goOff)
      window.removeEventListener('online', goOn)
    }
  }, [])

  if (!offline) return null

  return (
    <div
      role="status"
      className="safe-top sticky top-0 z-[60] bg-warning px-4 py-2 text-center text-[13px] font-semibold text-primary-dark"
    >
      Hors ligne — les actions seront impossibles jusqu’au retour du réseau.
    </div>
  )
}
