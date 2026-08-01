#!/usr/bin/env bash
# Checklist GO/NO-GO « pleine puissance » (lecture seule + tests légers).
set -euo pipefail
API="${API:-https://auta-gestion-api.onrender.com}"
FE="${FE:-https://reeegency-hub.github.io/auta-gestion/}"

pass=0; fail=0; warn=0
ok(){ echo "GO   | $1"; pass=$((pass+1)); }
ko(){ echo "NOGO | $1"; fail=$((fail+1)); }
wn(){ echo "WARN | $1"; warn=$((warn+1)); }

echo "=== AUTA Gestion — GO/NO-GO ==="
H=$(curl -sS -m 90 "$API/api/health" || echo '{}')
echo "$H" | jq -c .

echo "$H" | grep -q '"status":"ok"' && ok "API health" || ko "API health"
echo "$H" | grep -q '"registration_open":false' && ok "Inscription fermée" || ko "Inscription ouverte"
echo "$H" | grep -q '"supabase":true\|"s3":true' && ok "Stockage remote (Supabase/S3)" || ko "Stockage local seul"
echo "$H" | grep -q '"smtp":true' && ok "SMTP configuré" || ko "SMTP manquant"
echo "$H" | grep -q '"grok":true' && ok "Clé Grok présente" || wn "Pas de clé Grok"
echo "$H" | grep -q '"redis":true' && ok "Redis" || wn "Redis absent (OK pilote)"
echo "$H" | grep -q '"sentry":true' && ok "Sentry" || wn "Sentry absent (OK pilote)"

code=$(curl -sS -o /dev/null -w "%{http_code}" -m 30 "$FE")
[[ "$code" == "200" ]] && ok "Frontend Pages ($code)" || ko "Frontend ($code)"

t=$(curl -sS -m 90 -o /tmp/auta_go_login.json -w "%{time_total}" -X POST "$API/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"directeur@auta.gestion","password":"auta123"}' || echo 99)
python3 - <<PY
import json
d=json.load(open("/tmp/auta_go_login.json"))
ok=bool(d.get("access_token"))
print("token", ok)
open("/tmp/auta_go_token","w").write("1" if ok else "0")
PY
[[ "$(cat /tmp/auta_go_token)" == "1" ]] && ok "Login directeur" || ko "Login directeur"
python3 - <<PY
t=float("$t")
print(f"login_time={t:.2f}s")
open("/tmp/auta_go_time","w").write("fast" if t<3 else "slow")
PY
[[ "$(cat /tmp/auta_go_time)" == "fast" ]] && ok "Login < 3s (à chaud)" || wn "Login lent (cold start free probable)"

reg=$(curl -sS -m 30 -X POST "$API/api/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"garage_name":"Test Garage","full_name":"Test","email":"nogo@example.com","password":"test1234"}')
echo "$reg" | grep -qi 'fermée\|403\|Inscription' && ok "Register refusé" || wn "Register réponse: $reg"

echo
echo "=== Score: GO=$pass  NOGO=$fail  WARN=$warn ==="
[[ "$fail" -eq 0 ]] && echo "Verdict: GO pilote (voir WARN pour pleine puissance)" || echo "Verdict: NO-GO — corriger les NOGO"
