"""Capa de IA local: Isolation Forest sobre variables por ventana de tiempo.

En la arquitectura real este script lee las métricas desde InfluxDB y escribe el
puntaje de vuelta como la medición `ia_anomalias`. En el prototipo construye las
mismas variables a partir de los eventos del paquete. No envía datos a la nube.
"""
from __future__ import annotations

import math
from collections import defaultdict
from datetime import timedelta

from comun import es_interna, nombre_activo, severidad

VARIABLES = [
    "eventos", "fallos", "exitos", "bloqueos", "usuarios_distintos", "puertos_distintos",
    "destinos_distintos", "destinos_sensibles", "log_bytes", "hora", "fuera_horario",
    "origen_interno",
]


def construir_ventanas(eventos: list[dict], inventario: dict, cfg: dict) -> list[dict]:
    minutos = cfg["ia"]["ventana_minutos"]
    sensibles = set(cfg["activos_sensibles"])
    grupos: dict[tuple, list[dict]] = defaultdict(list)
    for e in eventos:
        inicio = e["dt"].replace(minute=(e["dt"].minute // minutos) * minutos, second=0)
        grupos[(e["origen_ip"], inicio)].append(e)

    ventanas = []
    for (origen, inicio), evs in sorted(grupos.items(), key=lambda kv: (kv[0][1], kv[0][0])):
        hora = inicio.hour
        destinos = {nombre_activo(e["destino_ip"], inventario) for e in evs}
        ventanas.append({
            "ventana_inicio": inicio.isoformat(),
            "ventana_fin": (inicio + timedelta(minutes=minutos)).isoformat(),
            "origen_ip": origen,
            "origen_activo": nombre_activo(origen, inventario),
            "destinos": ", ".join(sorted(destinos)),
            "eventos_ids": ", ".join(e["evento_id"] for e in evs),
            "eventos": len(evs),
            "fallos": sum(e["resultado"] == "fallo" for e in evs),
            "exitos": sum(e["resultado"] == "exito" for e in evs),
            "bloqueos": sum(e["accion"] == "deny" for e in evs),
            "usuarios_distintos": len({e["usuario_prueba"] for e in evs} - {"-"}),
            "puertos_distintos": len({e["puerto_destino"] for e in evs}),
            "destinos_distintos": len(destinos),
            "destinos_sensibles": sum(d in sensibles for d in destinos),
            "log_bytes": round(math.log10(1 + sum(e["bytes"] for e in evs)), 4),
            "hora": hora,
            "fuera_horario": int(not cfg["hora_inicio"] <= hora < cfg["hora_fin"]),
            "origen_interno": int(es_interna(origen, cfg)),
        })
    return ventanas


def _explicar(v: dict, medianas: dict, dispersion: dict) -> str:
    """Variables que más se alejan de lo típico (distancia robusta a la mediana)."""
    distancias = []
    for k in VARIABLES:
        d = (v[k] - medianas[k]) / dispersion[k]
        if abs(d) >= 2:
            distancias.append((abs(d), f"{k}={v[k]} (típico {medianas[k]:g})"))
    distancias.sort(reverse=True)
    return "; ".join(t for _, t in distancias[:4]) or "combinación poco frecuente de variables"


def detectar(eventos: list[dict], inventario: dict, cfg: dict):
    """Entrena el modelo y devuelve (ventanas con puntaje, alertas de IA).
    Si scikit-learn no está instalado, devuelve las ventanas sin puntaje."""
    ventanas = construir_ventanas(eventos, inventario, cfg)
    try:
        from sklearn.ensemble import IsolationForest
    except ImportError:
        for v in ventanas:
            v.update(puntaje="", severidad_ia="sin_modelo", explicacion="scikit-learn no instalado")
        return ventanas, []

    ia = cfg["ia"]
    X = [[v[k] for k in VARIABLES] for v in ventanas]
    modelo = IsolationForest(n_estimators=ia["n_estimators"], contamination=ia["contamination"],
                             random_state=ia["random_state"])
    modelo.fit(X)
    puntajes = modelo.decision_function(X)   # negativo = anómalo

    medianas, dispersion = {}, {}
    for k in VARIABLES:
        col = sorted(v[k] for v in ventanas)
        med = col[len(col) // 2]
        mad = sorted(abs(x - med) for x in col)[len(col) // 2]
        medianas[k] = med
        dispersion[k] = mad if mad > 0 else (max(col) - min(col)) / 4 or 1

    alertas = []
    for v, p in zip(ventanas, puntajes):
        v["puntaje"] = round(float(p), 4)
        if p < ia["umbral_alta"]:
            v["severidad_ia"], regla, nivel = "alta", 100901, 12
        elif p < ia["umbral_media"]:
            v["severidad_ia"], regla, nivel = "media", 100900, 9
        else:
            v["severidad_ia"] = "normal"
            v["explicacion"] = ""
            continue
        v["explicacion"] = _explicar(v, medianas, dispersion)
        alertas.append({
            "alerta_id": f"IA{len(alertas) + 1:03}",
            "timestamp": v["ventana_inicio"] + "-05:00",
            "fecha_hora": v["ventana_inicio"],
            "regla_id": regla,
            "nivel": nivel,
            "severidad": severidad(nivel, cfg),
            "descripcion": "Comportamiento anómalo detectado por Isolation Forest",
            "origen_activo": v["origen_activo"],
            "srcip": v["origen_ip"],
            "destino_activo": v["destinos"],
            "eventos": v["eventos_ids"],
            "puntaje": v["puntaje"],
            "contexto": v["explicacion"],
        })
    return ventanas, alertas
