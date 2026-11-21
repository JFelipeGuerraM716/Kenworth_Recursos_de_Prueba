"""Escribe las salidas en los mismos formatos que usaría la cadena real:

- alerts.json: una alerta por línea con la estructura de /var/ossec/logs/alerts/alerts.json
  (es lo que Telegraf lee con inputs.tail).
- influx_line_protocol.txt: lo que Telegraf escribiría en InfluxDB (mediciones
  `wazuh_alertas` e `ia_anomalias`).
"""
from __future__ import annotations

import json
from datetime import datetime

from comun import ZONA_BOGOTA


def _ns(fecha_hora: str) -> int:
    return int(datetime.fromisoformat(fecha_hora).replace(tzinfo=ZONA_BOGOTA).timestamp()) * 10**9


def _tag(valor) -> str:
    return str(valor).replace("\\", "\\\\").replace(" ", "\\ ").replace(",", "\\,").replace("=", "\\=")


def alerta_wazuh(a: dict, inventario: dict) -> dict:
    agente_id = "000"
    if a["agente_ip"] in inventario:
        agente_id = inventario[a["agente_ip"]]["activo_id"][1:].zfill(3)
    return {
        "timestamp": datetime.fromisoformat(a["fecha_hora"]).strftime("%Y-%m-%dT%H:%M:%S.000-0500"),
        "rule": {"level": a["nivel"], "description": a["descripcion"], "id": str(a["regla_id"]),
                 "groups": ["kenworth_lab"] + a["grupos"],
                 **({"mitre": {"id": a["mitre"]}} if a["mitre"] else {})},
        "agent": {"id": agente_id, "name": a["agente"], "ip": a["agente_ip"]},
        "manager": {"name": "LOG-LAB"},
        "id": a["alerta_id"],
        "decoder": {"name": "kenworth-lab-normalizado"},
        "data": {"srcip": a["srcip"], "dstip": a["dstip"], "dstport": str(a["puerto"]),
                 "action": a["accion"], "fw_rule": a["regla_fw"], "dstuser": a["usuario"],
                 "result": a["resultado"], "bytes": str(a["bytes"]), "evento_id": a["evento_id"]},
        "location": "02_Datos/eventos_normalizados.csv",
        "full_log": a["contexto"],
    }


def escribir_alerts_json(ruta, alertas: list[dict], inventario: dict) -> None:
    with ruta.open("w", encoding="utf-8") as f:
        for a in alertas:
            f.write(json.dumps(alerta_wazuh(a, inventario), ensure_ascii=False) + "\n")


def escribir_line_protocol(ruta, alertas: list[dict], ventanas: list[dict]) -> None:
    lineas = []
    for a in alertas:
        tags = (f"agente={_tag(a['agente'])},regla={a['regla_id']},nivel={a['nivel']},"
                f"severidad={a['severidad']},srcip={_tag(a['srcip'])},destino={_tag(a['destino_activo'])}")
        lineas.append(f"wazuh_alertas,{tags} conteo=1i,nivel_num={a['nivel']}i,bytes={a['bytes']}i "
                      f"{_ns(a['fecha_hora'])}")
    for v in ventanas:
        if v.get("puntaje") == "":
            continue
        tags = f"origen={_tag(v['origen_ip'])},severidad={v['severidad_ia']}"
        lineas.append(f"ia_anomalias,{tags} puntaje={v['puntaje']},eventos={v['eventos']}i,"
                      f"fallos={v['fallos']}i,bloqueos={v['bloqueos']}i {_ns(v['ventana_inicio'])}")
    ruta.write_text("\n".join(lineas) + "\n", encoding="utf-8")
