#!/bin/bash
# Audit production en lecture seule (pas de création de compte)
set -e
API="https://auta-gestion-api.onrender.com"
FE="https://reeegency-hub.github.io/auta-gestion/"
ORIGIN="https://reeegency-hub.github.io"
export PATH="$HOME/.local/bin:$PATH"

echo "========== 1. FRONTEND =========="
curl -sI "$FE" | head -12
JS=$(curl -s "$FE" | grep -oE '/auta-gestion/assets/index-[^"]+\.js' | head -1)
echo "JS=$JS"
curl -s "https://reeegency-hub.github.io${JS}" | grep -oE 'https://[a-zA-Z0-9.-]+onrender\.com' | sort -u | head -5
curl -s "https://reeegency-hub.github.io${JS}" | grep -o 'HashRouter\|BrowserRouter\|auta-gestion-api' | sort | uniq -c

echo
echo "========== 2. API HEALTH =========="
curl -s -m 90 "$API/api/health"; echo

echo
echo "========== 3. CORS preflight =========="
curl -sI -X OPTIONS "$API/api/auth/login" \
  -H "Origin: $ORIGIN" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: content-type" | grep -iE 'HTTP/|access-control'

echo
echo "========== 4. LOGIN DEMO =========="
LOGIN=$(curl -s -m 60 -X POST "$API/api/auth/login" \
  -H "Content-Type: application/json" \
  -H "Origin: $ORIGIN" \
  -d '{"email":"directeur@auta.demo","password":"auta123"}')
echo "$LOGIN" | head -c 400; echo
TOKEN=$(python3 -c "import json,sys; print(json.loads(sys.argv[1]).get('access_token',''))" "$LOGIN")
echo "TOKEN_LEN=${#TOKEN}"
if [ -z "$TOKEN" ]; then echo "LOGIN FAILED"; exit 1; fi

echo
echo "========== 5. ME + DASHBOARD =========="
curl -s -m 30 -H "Authorization: Bearer $TOKEN" -H "Origin: $ORIGIN" "$API/api/auth/me"; echo
curl -s -m 30 -H "Authorization: Bearer $TOKEN" "$API/api/dashboard"; echo

echo
echo "========== 6. LISTES =========="
python3 <<PY
import json,urllib.request
token="$TOKEN"
api="$API"
def get(path):
    req=urllib.request.Request(api+path, headers={"Authorization":"Bearer "+token})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)
ds=get("/api/dossiers")
print("dossiers:", len(ds) if isinstance(ds,list) else ds)
print("quotes:", len(get("/api/quotes")))
print("invoices:", len(get("/api/invoices")))
board=get("/api/workshop/board")
print("workshop open:", sum(len(v) for v in board.get("columns",{}).values()))
settings=get("/api/settings")
print("settings company:", settings.get("company_name"))
PY

echo
echo "========== 7. BAD PASSWORD =========="
curl -s -o /tmp/bad.json -w "bad_login_http:%{http_code}\n" -X POST "$API/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"directeur@auta.demo","password":"wrong"}'
cat /tmp/bad.json; echo

echo
echo "========== 8. CORS on login response =========="
curl -sI -X POST "$API/api/auth/login" \
  -H "Content-Type: application/json" \
  -H "Origin: $ORIGIN" \
  -d '{"email":"directeur@auta.demo","password":"auta123"}' | grep -iE 'HTTP/|access-control'

echo
echo "========== 9. PAGES =========="
gh run list -R reeegency-hub/auta-gestion --limit 3
curl -sI "https://reeegency-hub.github.io/auta-gestion/404.html" | head -6
echo "DONE"
