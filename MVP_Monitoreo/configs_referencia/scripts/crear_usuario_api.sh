#!/usr/bin/env bash
# Crea en la API de Wazuh el usuario de solo lectura que usa Telegraf.
# Se ejecuta en el equipo del Wazuh manager.
# Uso (desde configs_referencia):
#   WAZUH_ADMIN_USER=wazuh WAZUH_ADMIN_PASSWORD='...' bash scripts/crear_usuario_api.sh
set -euo pipefail
cd "$(dirname "$0")/.."
set -a; source .env; set +a
API=https://localhost:55000
CA=certs/ca.crt

TOKEN=$(curl -sS --fail --cacert "$CA" -u "${WAZUH_ADMIN_USER}:${WAZUH_ADMIN_PASSWORD}" \
  -X POST "$API/security/user/authenticate?raw=true")
H=(-H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json")

curl -sS --cacert "$CA" "${H[@]}" -X POST "$API/security/users" \
  -d "{\"username\": \"$WAZUH_API_USER\", \"password\": \"$WAZUH_API_PASSWORD\"}" > /dev/null

USER_ID=$(curl -sS --fail --cacert "$CA" "${H[@]}" "$API/security/users?search=$WAZUH_API_USER" \
  | python3 -c "import json,sys,os; u=[x for x in json.load(sys.stdin)['data']['affected_items'] if x['username']==os.environ['WAZUH_API_USER']]; print(u[0]['id'])")
ROLE_ID=$(curl -sS --fail --cacert "$CA" "${H[@]}" "$API/security/roles?search=readonly" \
  | python3 -c "import json,sys; r=[x for x in json.load(sys.stdin)['data']['affected_items'] if x['name']=='readonly']; print(r[0]['id'])")

curl -sS --fail --cacert "$CA" "${H[@]}" -X POST \
  "$API/security/users/$USER_ID/roles?role_ids=$ROLE_ID" > /dev/null
echo "Usuario $WAZUH_API_USER creado con el rol readonly (id $ROLE_ID)"
