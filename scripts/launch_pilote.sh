#!/usr/bin/env bash
# Lance la Phase 1 pilote sur Render via API.
# Usage:
#   export RENDER_API_KEY=rnd_...
#   export GROK_API_KEY=xai-...          # optionnel mais recommandé
#   ./scripts/launch_pilote.sh
#
# Prérequis: curl + jq. Compte Render avec paiement (Starter + Postgres).

set -euo pipefail

API="https://api.render.com/v1"
SERVICE_NAME="${SERVICE_NAME:-auta-gestion-api}"
DB_NAME="${DB_NAME:-auta-gestion-db}"
REGION="${REGION:-frankfurt}"
OWNER_ID="${OWNER_ID:-}"  # optional; auto-detected from first service if empty

need() { command -v "$1" >/dev/null || { echo "Manque: $1"; exit 1; }; }
need curl
need jq

if [[ -z "${RENDER_API_KEY:-}" ]]; then
  echo "❌ RENDER_API_KEY manquant."
  echo "   Crée une clé : https://dashboard.render.com/u/settings#api-keys"
  exit 1
fi

auth=(-H "Authorization: Bearer $RENDER_API_KEY" -H "Accept: application/json" -H "Content-Type: application/json")

echo "==> Lookup service $SERVICE_NAME"
SERVICES=$(curl -fsS "${auth[@]}" "$API/services?limit=50")
SERVICE_ID=$(echo "$SERVICES" | jq -r --arg n "$SERVICE_NAME" '
  [.[] | .service | select(.name==$n)] | .[0].id // empty')
if [[ -z "$SERVICE_ID" ]]; then
  echo "❌ Service '$SERVICE_NAME' introuvable."
  echo "$SERVICES" | jq -r '.[].service | "\(.id) \(.name) \(.type)"'
  exit 1
fi
echo "    service_id=$SERVICE_ID"

if [[ -z "$OWNER_ID" ]]; then
  OWNER_ID=$(echo "$SERVICES" | jq -r --arg id "$SERVICE_ID" '
    [.[] | .service | select(.id==$id)] | .[0].ownerId // empty')
fi
echo "    owner_id=$OWNER_ID"

echo "==> Lookup / create Postgres $DB_NAME"
PG_LIST=$(curl -fsS "${auth[@]}" "$API/postgres?limit=50" || echo '[]')
PG_ID=$(echo "$PG_LIST" | jq -r --arg n "$DB_NAME" '
  [.[] | .postgres | select(.name==$n)] | .[0].id // empty')

if [[ -z "$PG_ID" ]]; then
  echo "    Creating database $DB_NAME (basic-256mb, $REGION)..."
  CREATE_BODY=$(jq -n \
    --arg name "$DB_NAME" \
    --arg ownerId "$OWNER_ID" \
    --arg region "$REGION" \
    '{name:$name, ownerId:$ownerId, region:$region, plan:"basic_256mb", version:"16"}')
  # API plan names vary; try common aliases
  CREATED=$(curl -sS "${auth[@]}" -X POST "$API/postgres" -d "$CREATE_BODY")
  PG_ID=$(echo "$CREATED" | jq -r '.id // .postgres.id // empty')
  if [[ -z "$PG_ID" ]]; then
    echo "⚠️  Création auto échouée. Crée la DB manuellement puis relance."
    echo "$CREATED" | jq .
    echo "    Tentative plans alternatifs..."
    for plan in basic-256mb free; do
      CREATE_BODY=$(jq -n \
        --arg name "$DB_NAME" \
        --arg ownerId "$OWNER_ID" \
        --arg region "$REGION" \
        --arg plan "$plan" \
        '{name:$name, ownerId:$ownerId, region:$region, plan:$plan, version:"16"}')
      CREATED=$(curl -sS "${auth[@]}" -X POST "$API/postgres" -d "$CREATE_BODY")
      PG_ID=$(echo "$CREATED" | jq -r '.id // .postgres.id // empty')
      [[ -n "$PG_ID" ]] && break
    done
  fi
  [[ -z "$PG_ID" ]] && { echo "❌ Impossible de créer Postgres"; echo "$CREATED" | jq .; exit 1; }
  echo "    Attente provisionnement Postgres..."
  for i in $(seq 1 60); do
    ST=$(curl -fsS "${auth[@]}" "$API/postgres/$PG_ID" | jq -r '.status // .postgres.status // empty')
    echo "    status=$ST ($i)"
    [[ "$ST" == "available" || "$ST" == "live" || "$ST" == "Available" ]] && break
    sleep 5
  done
else
  echo "    postgres_id=$PG_ID (existe déjà)"
fi

echo "==> Fetch internal database URL"
PG_CONN=$(curl -fsS "${auth[@]}" "$API/postgres/$PG_ID/connection-info" 2>/dev/null || true)
DATABASE_URL=$(echo "$PG_CONN" | jq -r '.internalConnectionString // .connectionString // empty')
if [[ -z "$DATABASE_URL" ]]; then
  # fallback older endpoint shape
  PG_DETAIL=$(curl -fsS "${auth[@]}" "$API/postgres/$PG_ID")
  DATABASE_URL=$(echo "$PG_DETAIL" | jq -r '
    .connectionInfo.internalConnectionString
    // .postgres.connectionInfo.internalConnectionString
    // .database.connectionInfo.internalConnectionString
    // empty')
fi
if [[ -z "$DATABASE_URL" ]]; then
  echo "❌ Impossible de lire DATABASE_URL. Colle-la manuellement dans Render Environment."
  exit 1
fi
echo "    DATABASE_URL obtenu (masqué)"

echo "==> Upgrade service plan → starter (si possible)"
# Best-effort; billing may require dashboard
curl -sS "${auth[@]}" -X PATCH "$API/services/$SERVICE_ID" \
  -d '{"serviceDetails":{"plan":"starter"}}' >/tmp/render_plan.json || true
echo "    réponse plan: $(jq -c '{id:.id,plan:(.serviceDetails.plan // .plan // .)}' /tmp/render_plan.json 2>/dev/null || cat /tmp/render_plan.json | head -c 200)"

SECRET_KEY=$(openssl rand -hex 32)

echo "==> Set environment variables"
ENV_PAYLOAD=$(jq -n \
  --arg db "$DATABASE_URL" \
  --arg secret "$SECRET_KEY" \
  --arg cors "https://reeegency-hub.github.io,https://reeegency-hub.github.io/auta-gestion" \
  --arg grok "${GROK_API_KEY:-}" \
  --arg grok_url "${GROK_BASE_URL:-https://api.x.ai/v1}" \
  --arg grok_model "${GROK_MODEL:-grok-3-mini}" \
  '
  [
    {key:"DATABASE_URL", value:$db},
    {key:"SECRET_KEY", value:$secret},
    {key:"ALLOW_OPEN_REGISTRATION", value:"false"},
    {key:"UPLOAD_DIR", value:"/tmp/auta-uploads"},
    {key:"CORS_ORIGINS", value:$cors},
    {key:"PYTHON_VERSION", value:"3.11.9"},
    {key:"GROK_BASE_URL", value:$grok_url},
    {key:"GROK_MODEL", value:$grok_model}
  ]
  + (if $grok != "" then [{key:"GROK_API_KEY", value:$grok}] else [] end)
  ')

curl -fsS "${auth[@]}" -X PUT "$API/services/$SERVICE_ID/env-vars" \
  -d "$ENV_PAYLOAD" | jq -r '.[].envVar | "\(.key)=***"' 

echo "==> Trigger deploy"
curl -fsS "${auth[@]}" -X POST "$API/services/$SERVICE_ID/deploys" \
  -d '{"clearCache":"do_not_clear"}' | jq -c '{id,status}'

echo "==> Wait health"
HEALTH_URL="${HEALTH_URL:-https://auta-gestion-api.onrender.com/api/health}"
for i in $(seq 1 40); do
  BODY=$(curl -sS -m 20 "$HEALTH_URL" || true)
  echo "    [$i] $BODY"
  if echo "$BODY" | jq -e '.status=="ok"' >/dev/null 2>&1; then
    GROK=$(echo "$BODY" | jq -r '.grok')
    REG=$(echo "$BODY" | jq -r '.registration_open')
    echo ""
    echo "✅ Health OK"
    echo "   grok=$GROK  registration_open=$REG"
    if [[ "$REG" != "false" ]]; then
      echo "⚠️  registration encore ouverte — vérifie ALLOW_OPEN_REGISTRATION"
    fi
    if [[ "$GROK" != "true" ]]; then
      echo "⚠️  Grok off — exporte GROK_API_KEY et relance le script"
    fi
    exit 0
  fi
  sleep 15
done

echo "❌ Timeout health. Vérifie le dashboard Render (deploy logs)."
exit 1
