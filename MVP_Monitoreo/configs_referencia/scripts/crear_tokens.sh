#!/usr/bin/env bash
# Crea en InfluxDB un token por servicio con el mínimo permiso y los guarda en .env
#   Telegraf: solo escritura | Grafana: solo lectura | IA: lectura y escritura
# Requisito: el contenedor influxdb debe estar en marcha (docker compose up -d influxdb)
# Uso (desde configs_referencia):  bash scripts/crear_tokens.sh
set -euo pipefail
cd "$(dirname "$0")/.."
set -a; source .env; set +a

influx() {
  docker compose exec -T influxdb influx "$@" \
    --host https://localhost:8086 --skip-verify --token "$INFLUX_ADMIN_TOKEN"
}

BUCKET_ID=$(influx bucket list --org "$INFLUX_ORG" --name "$INFLUX_BUCKET" --json \
  | python3 -c "import json,sys; print(json.load(sys.stdin)[0]['id'])")

crear() {   # descripción  permisos...
  local desc=$1; shift
  influx auth create --org "$INFLUX_ORG" --description "$desc" "$@" --json \
    | python3 -c "import json,sys; print(json.load(sys.stdin)['token'])"
}

ESCRITURA=$(crear telegraf --write-bucket "$BUCKET_ID")
LECTURA=$(crear grafana --read-bucket "$BUCKET_ID")
IA=$(crear ia --read-bucket "$BUCKET_ID" --write-bucket "$BUCKET_ID")

sed -i "s|^INFLUX_WRITE_TOKEN=.*|INFLUX_WRITE_TOKEN=$ESCRITURA|" .env
sed -i "s|^INFLUX_READ_TOKEN=.*|INFLUX_READ_TOKEN=$LECTURA|" .env
sed -i "s|^INFLUX_IA_TOKEN=.*|INFLUX_IA_TOKEN=$IA|" .env
echo "Tokens creados y guardados en .env"
