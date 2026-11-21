#!/usr/bin/env bash
# Crea una CA interna y los certificados TLS del stack en ./certs
#   ca.crt / ca.key           autoridad certificadora del laboratorio
#   influxdb.crt / .key       InfluxDB (8086)
#   grafana.crt / .key        Nginx delante de Grafana (443)
#   wazuh-api.crt / .key      API de Wazuh (55000)
# Uso (desde configs_referencia):  bash scripts/generar_certs.sh
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p certs
cd certs

if [ ! -f ca.key ]; then
  openssl req -x509 -newkey rsa:4096 -nodes -days 1825 -sha256 \
    -keyout ca.key -out ca.crt -subj "/CN=Kenworth-LAB CA" \
    -addext "basicConstraints=critical,CA:TRUE" \
    -addext "keyUsage=critical,keyCertSign,cRLSign" \
    -addext "subjectKeyIdentifier=hash"
fi

emitir() {   # nombre  subjectAltName
  local nombre=$1 san=$2
  openssl req -new -newkey rsa:2048 -nodes -sha256 \
    -keyout "$nombre.key" -out "$nombre.csr" -subj "/CN=$nombre"
  cat > "$nombre.ext" <<EOF
basicConstraints=CA:FALSE
keyUsage=critical,digitalSignature,keyEncipherment
extendedKeyUsage=serverAuth
subjectAltName=$san
subjectKeyIdentifier=hash
authorityKeyIdentifier=keyid,issuer
EOF
  openssl x509 -req -in "$nombre.csr" -CA ca.crt -CAkey ca.key -CAcreateserial \
    -days 825 -sha256 -extfile "$nombre.ext" -out "$nombre.crt"
  rm -f "$nombre.csr" "$nombre.ext"
}

emitir influxdb  "DNS:influxdb,DNS:localhost,IP:127.0.0.1"
emitir grafana   "DNS:localhost,DNS:monitoreo.lab.local,IP:127.0.0.1"
emitir wazuh-api "DNS:host.docker.internal,DNS:localhost,IP:127.0.0.1"

# Los contenedores leen las llaves con su propio usuario: permiso de lectura
# solo en este laboratorio local. En producción usar un gestor de secretos.
chmod 644 ./*.crt influxdb.key grafana.key
chmod 600 ca.key wazuh-api.key
echo "Certificados creados en $(pwd)"
