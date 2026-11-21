#!/usr/bin/env bash
# Crea en Grafana los puntos de contacto y la política de notificación, usando su API:
#   alta  -> Telegram + correo, de inmediato
#   media -> solo correo, agrupado cada 30 minutos
#   baja  -> sin notificación (solo tablero)
# Requisito: Grafana en marcha (docker compose up -d) y accesible en https://localhost
# Uso (desde configs_referencia):  bash scripts/configurar_notificaciones.sh
set -euo pipefail
cd "$(dirname "$0")/.."
set -a; source .env; set +a

python3 - <<'EOF'
import base64, json, os, ssl, urllib.request, urllib.error

URL = "https://localhost"
CTX = ssl.create_default_context(cafile="certs/ca.crt")
AUTH = base64.b64encode(f"admin:{os.environ['GRAFANA_ADMIN_PASSWORD']}".encode()).decode()

def llamar(metodo, ruta, cuerpo):
    req = urllib.request.Request(URL + ruta, method=metodo, data=json.dumps(cuerpo).encode(),
                                 headers={"Authorization": f"Basic {AUTH}",
                                          "Content-Type": "application/json",
                                          "X-Disable-Provenance": "true"})
    return urllib.request.urlopen(req, context=CTX, timeout=15)

def punto_contacto(uid, nombre, tipo, ajustes):
    cuerpo = {"uid": uid, "name": nombre, "type": tipo, "settings": ajustes}
    try:
        llamar("POST", "/api/v1/provisioning/contact-points", cuerpo)
    except urllib.error.HTTPError:
        llamar("PUT", f"/api/v1/provisioning/contact-points/{uid}", cuerpo)
    print(f"  punto de contacto {nombre} ({tipo}) listo")

correo = os.environ["CORREO_ALERTAS"]
punto_contacto("telegram-alta", "telegram-y-correo", "telegram",
               {"bottoken": os.environ["TELEGRAM_BOT_TOKEN"],
                "chatid": str(os.environ["TELEGRAM_CHAT_ID"]),
                "parse_mode": "HTML"})
punto_contacto("correo-alta", "telegram-y-correo", "email",
               {"addresses": correo, "singleEmail": True})
punto_contacto("correo-media", "correo-agrupado", "email",
               {"addresses": correo, "singleEmail": True})

politica = {
    "receiver": "correo-agrupado",
    "group_by": ["alertname", "severidad"],
    "routes": [
        {"receiver": "telegram-y-correo", "object_matchers": [["severidad", "=", "alta"]],
         "group_wait": "0s", "group_interval": "1m", "repeat_interval": "1h"},
        {"receiver": "correo-agrupado", "object_matchers": [["severidad", "=", "media"]],
         "group_wait": "30s", "group_interval": "30m", "repeat_interval": "4h"},
    ],
}
llamar("PUT", "/api/v1/provisioning/policies", politica)
print("  política de notificación lista")
print("Notificaciones configuradas")
EOF
