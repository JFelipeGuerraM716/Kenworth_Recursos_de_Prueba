"""Enrutamiento de notificaciones según severidad (simulado).

Reproduce la política de Grafana Alerting de la propuesta:
  alta  -> Telegram inmediato + correo inmediato
  media -> correo agrupado cada N minutos
  baja  -> sin notificación; solo tablero y resumen diario
En el prototipo los mensajes se escriben en archivos; no se envía nada por internet.
La configuración real de puntos de contacto está en configs_referencia/grafana/.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta


def _linea(a: dict) -> str:
    return (f"[{a['severidad'].upper()} {a['nivel']}] {a['fecha_hora'][11:16]} regla {a['regla_id']} - "
            f"{a['descripcion']} | {a.get('origen_activo', '')} -> {a.get('destino_activo', '')}"
            + (f" | {a['contexto']}" if a.get("contexto") else ""))


def enrutar(alertas: list[dict], cfg: dict) -> tuple[list[dict], dict[str, list[str]]]:
    """Devuelve (registro de envíos, textos por canal)."""
    minutos = cfg["notificaciones"]["agrupar_medias_minutos"]
    registro: list[dict] = []
    textos: dict[str, list[str]] = defaultdict(list)
    ordenadas = sorted(alertas, key=lambda a: (a["fecha_hora"], a["alerta_id"]))

    for a in ordenadas:
        if a["severidad"] != "alta":
            continue
        cuerpo = _linea(a)
        for canal in cfg["notificaciones"]["alta"]:
            textos[canal].append(f"Para: equipo de monitoreo\n{cuerpo}\nAlerta {a['alerta_id']} - "
                                 "requiere revisión humana; no confirma incidente.\n")
            registro.append({"canal": canal, "envio": a["fecha_hora"], "severidad": "alta",
                             "n_alertas": 1, "alertas": a["alerta_id"], "asunto": a["descripcion"]})

    grupos: dict[datetime, list[dict]] = defaultdict(list)
    for a in ordenadas:
        if a["severidad"] == "media":
            dt = datetime.fromisoformat(a["fecha_hora"])
            inicio = dt.replace(minute=(dt.minute // minutos) * minutos, second=0)
            grupos[inicio].append(a)
    for inicio, grupo in sorted(grupos.items()):
        envio = (inicio + timedelta(minutes=minutos)).isoformat()
        cuerpo = "\n".join(_linea(a) for a in grupo)
        textos["correo_agrupado"].append(
            f"Asunto: [Kenworth-LAB] {len(grupo)} alertas medias entre {inicio:%H:%M} y "
            f"{inicio + timedelta(minutes=minutos):%H:%M}\n{cuerpo}\n")
        registro.append({"canal": "correo_agrupado", "envio": envio, "severidad": "media",
                         "n_alertas": len(grupo), "alertas": ", ".join(a["alerta_id"] for a in grupo),
                         "asunto": f"{len(grupo)} alertas medias"})

    bajas = [a for a in ordenadas if a["severidad"] == "baja"]
    if bajas:
        dia = bajas[0]["fecha_hora"][:10]
        conteo: dict[str, int] = defaultdict(int)
        for a in bajas:
            conteo[f"{a['regla_id']} - {a['descripcion']}"] += 1
        cuerpo = "\n".join(f"  {n:>3}  {r}" for r, n in sorted(conteo.items(), key=lambda x: -x[1]))
        textos["resumen_diario"].append(
            f"Resumen diario {dia}: {len(bajas)} alertas bajas (no notificadas en tiempo real)\n{cuerpo}\n")
        registro.append({"canal": "resumen_diario", "envio": f"{dia}T23:59:00", "severidad": "baja",
                         "n_alertas": len(bajas), "alertas": ", ".join(a["alerta_id"] for a in bajas),
                         "asunto": f"Resumen diario {dia}"})
    registro.sort(key=lambda r: (r["envio"], r["canal"]))
    return registro, textos
