#!/usr/bin/env bash
# Applique les variables S3/R2 sur le service Render auta-gestion-api.
# Usage:
#   export RENDER_API_KEY=rnd_...
#   export S3_BUCKET=auta-gestion
#   export S3_ACCESS_KEY=...
#   export S3_SECRET_KEY=...
#   export S3_ENDPOINT_URL=https://ACCOUNT_ID.r2.cloudflarestorage.com
#   export S3_REGION=auto          # défaut
#   ./scripts/apply_s3_env.sh

set -euo pipefail
need() { command -v "$1" >/dev/null || { echo "Manque: $1"; exit 1; }; }
need curl; need jq

: "${RENDER_API_KEY:?}"
: "${S3_BUCKET:?}"
: "${S3_ACCESS_KEY:?}"
: "${S3_SECRET_KEY:?}"
: "${S3_ENDPOINT_URL:?}"

SERVICE_ID="${SERVICE_ID:-srv-d9mvnsnlk1mc73dge800}"
API="https://api.render.com/v1"
auth=(-H "Authorization: Bearer $RENDER_API_KEY" -H "Accept: application/json" -H "Content-Type: application/json")

CUR=$(curl -fsS "${auth[@]}" "$API/services/$SERVICE_ID/env-vars")
BASE=$(echo "$CUR" | jq '[.[] | .envVar | {key, value}]')

EXTRA=$(jq -n \
  --arg bucket "$S3_BUCKET" \
  --arg region "${S3_REGION:-auto}" \
  --arg endpoint "$S3_ENDPOINT_URL" \
  --arg ak "$S3_ACCESS_KEY" \
  --arg sk "$S3_SECRET_KEY" \
  --arg prefix "${S3_PREFIX:-auta}" \
  '[
    {key:"S3_BUCKET", value:$bucket},
    {key:"S3_REGION", value:$region},
    {key:"S3_ENDPOINT_URL", value:$endpoint},
    {key:"S3_ACCESS_KEY", value:$ak},
    {key:"S3_SECRET_KEY", value:$sk},
    {key:"S3_PREFIX", value:$prefix}
  ]')

# Merge: replace existing S3_* keys, keep others
MERGED=$(jq -n --argjson base "$BASE" --argjson extra "$EXTRA" '
  ($base | map(select(.key | startswith("S3_") | not))) + $extra
')

echo "$MERGED" | jq -r '.[].key'
curl -fsS "${auth[@]}" -X PUT "$API/services/$SERVICE_ID/env-vars" -d "$MERGED" \
  | jq -r '.[].envVar.key' | grep '^S3_' || true

curl -fsS "${auth[@]}" -X POST "$API/services/$SERVICE_ID/deploys" \
  -d '{"clearCache":"do_not_clear"}' | jq '{id,status}'

echo "Attente health s3:true..."
for i in $(seq 1 40); do
  H=$(curl -sS -m 45 "https://auta-gestion-api.onrender.com/api/health" || true)
  echo "[$i] $H"
  echo "$H" | grep -q '"s3":true' && { echo "✅ S3/R2 actif"; exit 0; }
  sleep 12
done
echo "⚠️  Timeout — vérifie les logs Render"
exit 1
