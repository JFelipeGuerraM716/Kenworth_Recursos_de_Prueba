"""Utilidades compartidas: lectura de archivos del paquete y clasificación por severidad.

El prototipo es offline: solo lee archivos locales y escribe en MVP_Monitoreo/salidas.
"""
from __future__ import annotations

import csv
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]          # carpeta del paquete Kenworth
MVP = RAIZ / "MVP_Monitoreo"
SALIDAS = MVP / "salidas"
ZONA_BOGOTA = timezone(timedelta(hours=-5))


def leer_csv(ruta: Path) -> list[dict]:
    with ruta.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def escribir_csv(ruta: Path, filas: list[dict], campos: list[str]) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with ruta.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=campos, extrasaction="ignore")
        w.writeheader()
        w.writerows(filas)


def cargar_config() -> dict:
    return json.loads((MVP / "pipeline" / "config_mvp.json").read_text(encoding="utf-8"))


def cargar_eventos() -> list[dict]:
    """Usa solo el CSV. El JSONL es el MISMO conjunto en otro formato: no se suman."""
    eventos = leer_csv(RAIZ / "02_Datos" / "eventos_normalizados.csv")
    for e in eventos:
        e["dt"] = datetime.fromisoformat(e["fecha_hora"])
        e["puerto_destino"] = int(e["puerto_destino"])
        e["bytes"] = int(e["bytes"])
    return sorted(eventos, key=lambda e: (e["dt"], e["evento_id"]))


def cargar_inventario() -> dict[str, dict]:
    """Devuelve un diccionario IP -> activo."""
    return {a["ip_prueba"]: a for a in leer_csv(RAIZ / "02_Datos" / "inventario_activos.csv")}


def cargar_cambios() -> list[dict]:
    cambios = leer_csv(RAIZ / "02_Datos" / "cambios_autorizados.csv")
    for c in cambios:
        c["inicio_dt"] = datetime.fromisoformat(c["inicio"])
        c["fin_dt"] = datetime.fromisoformat(c["fin"])
    return cambios


def severidad(nivel: int, cfg: dict) -> str:
    for nombre, (bajo, alto) in cfg["severidad"].items():
        if bajo <= nivel <= alto:
            return nombre
    raise ValueError(f"Nivel fuera de rango 0-15: {nivel}")


def es_interna(ip: str, cfg: dict) -> bool:
    return any(ip.startswith(prefijo) for prefijo in cfg["redes_internas"])


def nombre_activo(ip: str, inventario: dict) -> str:
    return inventario[ip]["nombre_prueba"] if ip in inventario else f"externo:{ip}"
