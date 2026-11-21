#!/bin/sh
# REFERENCIA: obtiene un JWT de la API de Wazuh y lo renueva antes de que venza.
# El token se escribe en /run/wazuh/token, que Telegraf lee con token_file.
# La contraseña viaja solo en esta autenticación; las consultas usan el token.
set -eu
DURACION=900          # vigencia del token en segundos (auth_token_exp_timeout)
MARGEN=120            # renovar 2 minutos antes de que venza

while true; do
  if curl -sS --fail --cacert /etc/ssl/certs/monitoreo-ca.crt \
       -u "${WAZUH_API_USER}:${WAZUH_API_PASSWORD}" \
       -X POST "${WAZUH_API_URL}/security/user/authenticate?raw=true" \
       -o /run/wazuh/token.tmp; then
    mv /run/wazuh/token.tmp /run/wazuh/token
    sleep $((DURACION - MARGEN))
  else
    echo "No se pudo obtener el token; reintento en 30 s" >&2
    sleep 30
  fi
done
