#!/usr/bin/env bash
# Branche Supabase Storage sur Render + crée le bucket.
# Usage:
#   export RENDER_API_KEY=rnd_...
#   export SUPABASE_URL=https://xxxx.supabase.co
#   export SUPABASE_SERVICE_ROLE_KEY=eyJ...
#   export SUPABASE_BUCKET=auta   # optionnel
#   ./scripts/apply_supabase_env.sh

set -euo pipefail
need() { command -v "$1" >/dev/null || { echo "Manque: $1"; exit 1; }; }
need curl; need jq

: "${RENDER_API_KEY:?}"
: "${SUPABASE_URL:?}"
: "${SUPABASE_SERVICE_ROLE_KEY:?}"
BUCKET="${SUPABASE_BUCKET:-auta}"

SERVICE_ID="${SERVICE_ID:-srv-d9mvnsnlk1mc73dge800}"
API="https://api.render.com/v1"
auth=(-H "Authorization: Bearer $RENDER_API_KEY" -H "Accept: application/json" -H "Content-Type: application/json")

echo "==> Create/ensure Supabase bucket '$BUCKET'"
CREATE=$(curl -sS -X POST "${SUPABASE_URL%/}/storage/v1/bucket" \
  -H "Authorization: Bearer $SUPABASE_SERVICE_ROLE_KEY" \
  -H "apikey: $SUPABASE_SERVICE_ROLE_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"id\":\"$BUCKET\",\"name\":\"$BUCKET\",\"public\":false}")
echo "$CREATE" | head -c 300; echo

echo "==> Update Render env"
CUR=$(curl -fsS "${auth[@]}" "$API/services/$SERVICE_ID/env-vars")
BASE=$(echo "$CUR" | jq '[.[] | .envVar | {key, value}]')
EXTRA=$(jq -n \
  --arg url "$SUPABASE_URL" \
  --arg key "$SUPABASE_SERVICE_ROLE_KEY" \
  --arg bucket "$BUCKET" \
  '[
    {key:"SUPABASE_URL", value:$url},
    {key:"SUPABASE_SERVICE_ROLE_KEY", value:$key},
    {key:"SUPABASE_BUCKET", value:$bucket},
    {key:"S3_PREFIX", value:"auta"}
  ]')
MERGED=$(jq -n --argjson base "$BASE" --argjson extra "$EXTRA" '
  ($base | map(select(.key | startswith("SUPABASE_") | not))) + $extra
')
curl -fsS "${auth[@]}" -X PUT "$API/services/$SERVICE_ID/env-vars" -d "$MERGED" \
  | jq -r '.[].envVar.key' | grep '^SUPABASE_' || true

curl -fsS "${auth[@]}" -X POST "$API/services/$SERVICE_ID/deploys" \
  -d '{"clearCache":"do_not_clear"}' | jq '{id,status}'

echo "Attente health supabase:true..."
for i in $(seq 1 40); do
  H=$(curl -sS -m 45 "https://auta-gestion-api.onrender.com/api/health" || true)
  echo "[$i] $H"
  echo "$H" | grep -q '"supabase":true' && { echo "✅ Supabase Storage actif"; exit 0; }
  sleep 12
done
echo "⚠️  Timeout — le code avec supabase dans /health doit être déployé"
exit 1
