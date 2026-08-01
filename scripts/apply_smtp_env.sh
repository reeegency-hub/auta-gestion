#!/usr/bin/env bash
# Applique SMTP sur Render pour Phase 4.
# Usage:
#   export RENDER_API_KEY=rnd_...
#   export SMTP_HOST=smtp-relay.brevo.com
#   export SMTP_PORT=587
#   export SMTP_USER=...
#   export SMTP_PASSWORD=...
#   export SMTP_FROM="AUTA Gestion <devis@tongarage.fr>"
#   ./scripts/apply_smtp_env.sh

set -euo pipefail
need() { command -v "$1" >/dev/null || { echo "Manque: $1"; exit 1; }; }
need curl; need jq

: "${RENDER_API_KEY:?}"
: "${SMTP_HOST:?}"
: "${SMTP_USER:?}"
: "${SMTP_PASSWORD:?}"

SERVICE_ID="${SERVICE_ID:-srv-d9mvnsnlk1mc73dge800}"
API="https://api.render.com/v1"
auth=(-H "Authorization: Bearer $RENDER_API_KEY" -H "Accept: application/json" -H "Content-Type: application/json")

CUR=$(curl -fsS "${auth[@]}" "$API/services/$SERVICE_ID/env-vars")
BASE=$(echo "$CUR" | jq '[.[] | .envVar | {key, value}]')

EXTRA=$(jq -n \
  --arg host "$SMTP_HOST" \
  --arg port "${SMTP_PORT:-587}" \
  --arg user "$SMTP_USER" \
  --arg pass "$SMTP_PASSWORD" \
  --arg from "${SMTP_FROM:-$SMTP_USER}" \
  --arg tls "${SMTP_TLS:-true}" \
  '[
    {key:"SMTP_HOST", value:$host},
    {key:"SMTP_PORT", value:$port},
    {key:"SMTP_USER", value:$user},
    {key:"SMTP_PASSWORD", value:$pass},
    {key:"SMTP_FROM", value:$from},
    {key:"SMTP_TLS", value:$tls}
  ]')

MERGED=$(jq -n --argjson base "$BASE" --argjson extra "$EXTRA" '
  ($base | map(select(.key | startswith("SMTP_") | not))) + $extra
')

curl -fsS "${auth[@]}" -X PUT "$API/services/$SERVICE_ID/env-vars" -d "$MERGED" \
  | jq -r '.[].envVar.key' | grep '^SMTP_' || true

curl -fsS "${auth[@]}" -X POST "$API/services/$SERVICE_ID/deploys" \
  -d '{"clearCache":"do_not_clear"}' | jq '{id,status}'

echo "Attente health smtp:true..."
for i in $(seq 1 40); do
  H=$(curl -sS -m 45 "https://auta-gestion-api.onrender.com/api/health" || true)
  echo "[$i] $H"
  echo "$H" | grep -q '"smtp":true' && { echo "✅ SMTP actif"; exit 0; }
  sleep 12
done
echo "⚠️  Timeout — vérifie les logs Render / redeploy"
exit 1
