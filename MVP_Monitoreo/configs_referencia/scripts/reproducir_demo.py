"""Modo demostración: reproduce las alertas y puntajes de IA del prototipo con la hora actual.

Lee  MVP_Monitoreo/salidas/alerts.json  y  MVP_Monitoreo/salidas/anomalias_ia.csv
y los va escribiendo en  configs_referencia/demo/alerts.json  y  demo/ia.lp,
que Telegraf está vigilando. Así se prueba la cadena completa
Telegraf -> InfluxDB -> Grafana -> Telegram/correo sin agentes reales.

Uso (desde la carpeta principal del paquete):
    python3 MVP_Monitoreo/configs_referencia/scripts/reproducir_demo.py --velocidad 60
--velocidad 60 reproduce un minuto de los datos en un segundo (el día de prueba dura ~8 min).
"""
import argparse
import csv
import json
import time
from datetime import datetime, timezone
from pathlib import Path

MVP = Path(__file__).resolve().parents[2]
DEMO = MVP / "configs_referencia" / "demo"


def tag(valor: str) -> str:
    return valor.replace(" ", "\\ ").replace(",", "\\,").replace("=", "\\=")


def cargar():
    eventos = []
    for linea in (MVP / "salidas" / "alerts.json").read_text(encoding="utf-8").splitlines():
        a = json.loads(linea)
        eventos.append((datetime.strptime(a["timestamp"], "%Y-%m-%dT%H:%M:%S.%f%z"), "alerta", a))
    with (MVP / "salidas" / "anomalias_ia.csv").open(encoding="utf-8-sig", newline="") as f:
        for v in csv.DictReader(f):
            if v["puntaje"]:
                dt = datetime.fromisoformat(v["ventana_inicio"] + "-05:00")
                eventos.append((dt, "ia", v))
    return sorted(eventos, key=lambda e: e[0])


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--velocidad", type=float, default=60.0)
    args = p.parse_args()

    eventos = cargar()
    inicio_datos = eventos[0][0]
    inicio_real = time.time()
    DEMO.mkdir(exist_ok=True)
    print(f"Reproduciendo {len(eventos)} registros a velocidad x{args.velocidad:g}")
    with (DEMO / "alerts.json").open("a", encoding="utf-8") as fa, (DEMO / "ia.lp").open("a", encoding="utf-8") as fi:
        for dt, tipo, dato in eventos:
            espera = (dt - inicio_datos).total_seconds() / args.velocidad - (time.time() - inicio_real)
            if espera > 0:
                time.sleep(espera)
            ahora = datetime.now(timezone.utc)
            if tipo == "alerta":
                dato = dict(dato, timestamp=ahora.astimezone().strftime("%Y-%m-%dT%H:%M:%S.000%z"))
                fa.write(json.dumps(dato, ensure_ascii=False) + "\n")
                fa.flush()
                print(f"  alerta {dato['id']} nivel {dato['rule']['level']}: {dato['rule']['description']}")
            else:
                ns = int(ahora.timestamp() * 1e9)
                fi.write(f"ia_anomalias,origen={tag(dato['origen_ip'])},severidad={dato['severidad_ia']} "
                         f"puntaje={dato['puntaje']},eventos={dato['eventos']}i,fallos={dato['fallos']}i {ns}\n")
                fi.flush()
    print("Fin de la demostración")


if __name__ == "__main__":
    main()
