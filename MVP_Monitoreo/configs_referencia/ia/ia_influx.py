"""REFERENCIA: capa de IA local conectada a InfluxDB (no se ejecuta en el laboratorio).

Modo entrenamiento (una vez, con un periodo considerado normal):
    python ia_influx.py entrenar --dias 7
Modo detección (bucle cada 5 minutos):
    python ia_influx.py detectar

Lee la medición `wazuh_eventos`, arma variables por IP de origen y ventana de 10 min,
aplica Isolation Forest y escribe el puntaje en la medición `ia_anomalias`.
No envía datos fuera del servidor.
"""
import math
import os
import sys
import time

import joblib
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
from sklearn.ensemble import IsolationForest

BUCKET = os.environ["INFLUX_BUCKET"]
MODELO = "/modelo/isolation_forest.joblib"
VARIABLES = ["eventos", "fallos", "exitos", "bloqueos", "usuarios_distintos", "puertos_distintos",
             "destinos_distintos", "log_bytes", "hora", "fuera_horario", "origen_interno"]

FLUX = """
from(bucket: "{bucket}")
  |> range(start: {inicio})
  |> filter(fn: (r) => r._measurement == "wazuh_eventos")
  |> pivot(rowKey: ["_time", "srcip", "agente"], columnKey: ["_field"], valueColumn: "_value")
  |> window(every: 10m)
  |> group(columns: ["_start", "srcip"])
"""


def cliente():
    return InfluxDBClient(url=os.environ["INFLUX_URL"], token=os.environ["INFLUX_IA_TOKEN"],
                          org=os.environ["INFLUX_ORG"], ssl_ca_cert=os.environ.get("SSL_CA_CERT"))


def ventanas(api, inicio: str):
    filas = []
    for tabla in api.query(FLUX.format(bucket=BUCKET, inicio=inicio)):
        regs = [r.values for r in tabla.records]
        if not regs:
            continue
        hora = regs[0]["_start"].astimezone().hour
        srcip = regs[0].get("srcip") or "desconocido"
        filas.append({
            "srcip": srcip,
            "inicio": regs[0]["_start"],
            "eventos": len(regs),
            "fallos": sum(r.get("resultado") == "fallo" for r in regs),
            "exitos": sum(r.get("resultado") == "exito" for r in regs),
            "bloqueos": sum(r.get("accion") == "deny" for r in regs),
            "usuarios_distintos": len({r.get("usuario") for r in regs} - {None, "-"}),
            "puertos_distintos": len({r.get("puerto") for r in regs} - {None}),
            "destinos_distintos": len({r.get("agente") for r in regs}),
            "log_bytes": math.log10(1 + sum(r.get("bytes") or 0 for r in regs)),
            "hora": hora,
            "fuera_horario": int(not 7 <= hora < 19),
            "origen_interno": int(srcip.startswith("10.60.")),
        })
    return filas


def entrenar(dias: int):
    with cliente() as c:
        datos = ventanas(c.query_api(), f"-{dias}d")
    modelo = IsolationForest(n_estimators=200, contamination="auto", random_state=42)
    modelo.fit([[v[k] for k in VARIABLES] for v in datos])
    joblib.dump(modelo, MODELO)
    print(f"Modelo entrenado con {len(datos)} ventanas")


def detectar():
    modelo = joblib.load(MODELO)
    with cliente() as c:
        escritura = c.write_api(write_options=SYNCHRONOUS)
        while True:
            datos = ventanas(c.query_api(), "-10m")
            if datos:
                puntajes = modelo.decision_function([[v[k] for k in VARIABLES] for v in datos])
                puntos = []
                for v, p in zip(datos, puntajes):
                    sev = "alta" if p < -0.25 else "media" if p < -0.15 else "normal"
                    puntos.append(Point("ia_anomalias").tag("origen", v["srcip"]).tag("severidad", sev)
                                  .field("puntaje", float(p)).field("eventos", v["eventos"])
                                  .field("fallos", v["fallos"]).time(v["inicio"]))
                escritura.write(bucket=BUCKET, record=puntos)
            time.sleep(300)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "entrenar":
        entrenar(int(sys.argv[sys.argv.index("--dias") + 1]) if "--dias" in sys.argv else 7)
    else:
        detectar()
