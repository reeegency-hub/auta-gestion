export const WORKSHOP_LABELS = {
  reception: 'Réception',
  carrosserie: 'Carrosserie',
  preparation: 'Préparation',
  peinture: 'Peinture',
  remontage: 'Remontage',
  controle_qualite: 'Contrôle qualité',
  pret_a_livrer: 'Prêt à livrer',
  livre: 'Livré',
}

export const WORKSHOP_ORDER = Object.keys(WORKSHOP_LABELS)

export const WORKSHOP_TONES = {
  reception: 'info',
  carrosserie: 'neutral',
  preparation: 'warn',
  peinture: 'warn',
  remontage: 'info',
  controle_qualite: 'info',
  pret_a_livrer: 'ok',
  livre: 'ok',
}

export const QUOTE_LABELS = {
  brouillon: 'Brouillon',
  en_attente: 'En attente',
  accepte: 'Accepté',
  refuse: 'Refusé',
}

export const QUOTE_TONES = {
  brouillon: 'neutral',
  en_attente: 'warn',
  accepte: 'ok',
  refuse: 'danger',
}

export const INVOICE_LABELS = {
  emise: 'Émise',
  en_attente: 'En attente',
  payee: 'Payée',
}

export const EXTRACTION_LABELS = {
  pending: 'En attente',
  processing: 'Analyse…',
  draft: 'À vérifier',
  validated: 'Validé',
  failed: 'Échec',
}

export const OP_TYPES = [
  { value: 'piece_remplacer', label: 'Pièce à remplacer' },
  { value: 'piece_reparer', label: 'Pièce à réparer' },
  { value: 'main_doeuvre', label: 'Main d’œuvre' },
  { value: 'peinture', label: 'Peinture' },
  { value: 'annexe', label: 'Annexe' },
]

export function money(v) {
  return new Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'EUR' }).format(v || 0)
}
