"""Ejecuta la cadena completa del prototipo offline.

    python MVP_Monitoreo/pipeline/run_mvp.py

Etapas (equivalencia con la arquitectura real):
  1. Eventos del paquete            -> lo que envían los agentes Wazuh (1514/TCP)
  2. reglas.evaluar                 -> Wazuh manager: reglas y nivel 0-15
  3. exportar.escribir_alerts_json  -> /var/ossec/logs/alerts/alerts.json
  4. exportar.escribir_line_protocol-> Telegraf escribe en InfluxDB (8086)
  5. anomalias.detectar             -> script de IA local (Isolation Forest)
  6. notificaciones.enrutar         -> Grafana Alerting (Telegram / correo)
  7. tablero.generar                -> paneles de Grafana
Solo lee archivos del paquete y escribe en MVP_Monitoreo/salidas. No usa internet.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import anomalias  # noqa: E402
import exportar  # noqa: E402
import notificaciones  # noqa: E402
import reglas  # noqa: E402
import tablero  # noqa: E402
from comun import (SALIDAS, cargar_cambios, cargar_config, cargar_eventos,  # noqa: E402
                   cargar_inventario, escribir_csv)

CAMPOS_ALERTA = ["alerta_id", "evento_id", "fecha_hora", "nivel", "severidad", "regla_id", "descripcion",
                 "coincidencias", "agente", "origen_activo", "srcip", "destino_activo", "dstip", "puerto",
                 "accion", "regla_fw", "usuario", "resultado", "bytes", "caso_id", "contexto"]


def main() -> dict:
    cfg = cargar_config()
    eventos, inventario, cambios = cargar_eventos(), cargar_inventario(), cargar_cambios()

    alertas, archivados = reglas.evaluar(eventos, inventario, cambios, cfg)
    casos = reglas.correlacionar(alertas, cfg)
    ventanas, alertas_ia = anomalias.detectar(eventos, inventario, cfg)
    envios, textos = notificaciones.enrutar(alertas + alertas_ia, cfg)

    SALIDAS.mkdir(parents=True, exist_ok=True)
    (SALIDAS / "notificaciones").mkdir(exist_ok=True)
    filas = [{**a, "coincidencias": " ".join(a["coincidencias"])} for a in alertas]
    escribir_csv(SALIDAS / "alertas_mvp.csv", filas, CAMPOS_ALERTA)
    escribir_csv(SALIDAS / "casos.csv", casos, list(casos[0].keys()) if casos else ["caso_id"])
    escribir_csv(SALIDAS / "anomalias_ia.csv", ventanas,
                 ["ventana_inicio", "origen_ip", "origen_activo", "destinos", "puntaje", "severidad_ia",
                  "explicacion"] + anomalias.VARIABLES + ["eventos_ids"])
    escribir_csv(SALIDAS / "notificaciones.csv", envios,
                 ["envio", "canal", "severidad", "n_alertas", "alertas", "asunto"])
    for canal, mensajes in textos.items():
        (SALIDAS / "notificaciones" / f"{canal}.txt").write_text("\n".join(mensajes), encoding="utf-8")
    exportar.escribir_alerts_json(SALIDAS / "alerts.json", alertas, inventario)
    exportar.escribir_line_protocol(SALIDAS / "influx_line_protocol.txt", alertas, ventanas)
    tablero.generar(SALIDAS / "tablero.html", eventos, alertas, casos, ventanas, alertas_ia, envios, cfg)

    resumen = {
        "eventos": len(eventos),
        "eventos_archivados_sin_alerta": len(archivados),
        "alertas": len(alertas),
        "alertas_por_severidad": dict(Counter(a["severidad"] for a in alertas)),
        "alertas_por_regla": {str(k): v for k, v in sorted(Counter(a["regla_id"] for a in alertas).items())},
        "casos": len(casos),
        "ventanas_ia": len(ventanas),
        "anomalias_ia": dict(Counter(a["severidad"] for a in alertas_ia)),
        "notificaciones": dict(Counter(e["canal"] for e in envios)),
        "nota": "Datos de prueba. Alertas y casos requieren revisión humana; no son incidentes confirmados.",
    }
    (SALIDAS / "resumen_mvp.json").write_text(json.dumps(resumen, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(resumen, ensure_ascii=False, indent=2))
    return resumen


if __name__ == "__main__":
    main()
