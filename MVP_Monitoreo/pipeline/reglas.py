"""Motor de reglas que imita el comportamiento del Wazuh manager.

Igual que Wazuh, cada evento recibe UNA alerta con la regla de mayor nivel que coincide
(las demás quedan en «coincidencias»). Así un mismo evento no se cuenta dos veces.
Solo los eventos con nivel >= log_alert_level (3) se escriben como alertas; el resto
queda como evento archivado, igual que en /var/ossec/logs/archives.

Las reglas equivalentes en sintaxis Wazuh están en configs_referencia/wazuh/local_rules.xml.
"""
from __future__ import annotations

from collections import defaultdict, deque
from datetime import datetime, timedelta

from comun import es_interna, nombre_activo, severidad

# id: (nivel, descripción, grupos, MITRE ATT&CK relacionado)
REGLAS: dict[int, tuple[int, str, list[str], list[str]]] = {
    100001: (2, "Tráfico web previsto hacia la DMZ (R01)", ["firewall", "web"], []),
    100010: (5, "Conexión bloqueada por el cierre por defecto (R04)", ["firewall", "bloqueo"], []),
    100011: (6, "Conexión bloqueada hacia un activo sensible", ["firewall", "bloqueo"], []),
    100012: (10, "Posible reconocimiento: bloqueos repetidos a varios puertos de un activo sensible",
             ["firewall", "reconocimiento"], ["T1046"]),
    100020: (5, "Fallo de autenticación", ["autenticacion"], []),
    100021: (10, "Fallos de autenticación repetidos (umbral en ventana móvil)",
             ["autenticacion", "fuerza_bruta"], ["T1110"]),
    100022: (12, "Acceso exitoso después de fallos repetidos",
             ["autenticacion", "fuerza_bruta"], ["T1110", "T1078"]),
    100023: (3, "Acceso exitoso dentro del horario de prueba", ["autenticacion"], []),
    100030: (8, "Acceso exitoso fuera del horario de prueba", ["autenticacion", "horario"], ["T1078"]),
    100031: (4, "Acceso fuera de horario dentro de un cambio autorizado; cierre por revisión humana",
             ["autenticacion", "cambio_autorizado"], []),
    100040: (10, "Volumen alto para revisión", ["volumen"], []),
    100041: (13, "Volumen alto desde un activo sensible hacia un destino externo",
             ["volumen", "posible_exfiltracion"], ["T1048"]),
    100042: (14, "Envío externo desde un activo en cambio autorizado que no cubre envíos externos",
             ["volumen", "cambio_autorizado"], ["T1048"]),
    100050: (7, "El flujo registrado no corresponde a la descripción de R01 (trazabilidad)",
             ["trazabilidad", "politica"], []),
    100060: (7, "Uso de la excepción R02 (Usuarios -> DB-LAB any, sin registro)", ["politica"], []),
}


def _cambio_vigente(e: dict, cambios: list[dict]) -> dict | None:
    """Cambio autorizado cuya ventana incluye el evento y cuyo activo participa en él."""
    for c in cambios:
        if c["inicio_dt"] <= e["dt"] <= c["fin_dt"]:
            return c
    return None


def evaluar(eventos: list[dict], inventario: dict, cambios: list[dict], cfg: dict):
    """Devuelve (alertas, archivados). Cada evento produce exactamente una decisión."""
    ventana = timedelta(minutes=cfg["ventana_minutos"])
    sensibles = set(cfg["activos_sensibles"])
    ip_por_nombre = {a["nombre_prueba"]: ip for ip, a in inventario.items()}

    fallos = defaultdict(deque)        # (origen, destino, usuario) -> tiempos de fallos
    fallos_disparo = {}                # última vez que disparó 100021 por clave
    bloqueos = defaultdict(deque)      # (origen, destino) -> (tiempo, puerto)
    bloqueos_disparo = {}

    alertas, archivados = [], []
    for e in eventos:
        dt = e["dt"]
        origen = nombre_activo(e["origen_ip"], inventario)
        destino = nombre_activo(e["destino_ip"], inventario)
        coincide: list[int] = []
        contexto: list[str] = []

        # --- Tráfico web previsto -------------------------------------------------
        if (e["tipo"] == "trafico" and e["accion"] == "allow" and e["regla_id"] == "R01"
                and destino == "WEB-LAB" and e["puerto_destino"] == 443):
            coincide.append(100001)

        # --- Bloqueos del firewall ------------------------------------------------
        if e["accion"] == "deny":
            coincide.append(100011 if destino in sensibles else 100010)
            clave = (e["origen_ip"], e["destino_ip"])
            q = bloqueos[clave]
            q.append((dt, e["puerto_destino"]))
            while q and dt - q[0][0] > ventana:
                q.popleft()
            puertos = {p for _, p in q}
            ultimo = bloqueos_disparo.get(clave)
            if (destino in sensibles and len(q) >= cfg["bloqueos_umbral"]
                    and len(puertos) >= cfg["puertos_distintos_reconocimiento"]
                    and (ultimo is None or dt - ultimo > ventana)):
                coincide.append(100012)
                bloqueos_disparo[clave] = dt
                contexto.append(f"{len(q)} bloqueos en {cfg['ventana_minutos']} min a puertos "
                                f"{sorted(puertos)}; el firewall los bloqueó: no prueba intrusión")

        # --- Autenticación --------------------------------------------------------
        if e["tipo"] == "autenticacion":
            clave = (e["origen_ip"], e["destino_ip"], e["usuario_prueba"])
            q = fallos[clave]
            while q and dt - q[0] > ventana:
                q.popleft()
            if e["resultado"] == "fallo":
                coincide.append(100020)
                q.append(dt)
                ultimo = fallos_disparo.get(clave)
                if len(q) >= cfg["fallos_umbral"] and (ultimo is None or dt - ultimo > ventana):
                    coincide.append(100021)
                    fallos_disparo[clave] = dt
                    contexto.append(f"{len(q)} fallos en ventana móvil de {cfg['ventana_minutos']} min "
                                    "(mismo origen, destino y usuario)")
            elif e["resultado"] == "exito":
                if len(q) >= cfg["fallos_umbral"]:
                    coincide.append(100022)
                    contexto.append(f"Éxito tras {len(q)} fallos en {cfg['ventana_minutos']} min; "
                                    "no prueba credenciales comprometidas")
                dentro = cfg["hora_inicio"] <= dt.hour < cfg["hora_fin"]
                if dentro:
                    coincide.append(100023)
                else:
                    cambio = _cambio_vigente(e, cambios)
                    if (cambio and ip_por_nombre.get(cambio["activo"]) == e["destino_ip"]
                            and cambio["origen_autorizado"] == e["origen_ip"]
                            and cambio["usuario_prueba"] == e["usuario_prueba"]):
                        coincide.append(100031)
                        contexto.append(f"Coincide con {cambio['cambio_id']} ({cambio['motivo']}); "
                                        "cerrar solo tras revisión humana")
                    else:
                        coincide.append(100030)

        # --- Volumen --------------------------------------------------------------
        if e["bytes"] >= cfg["volumen_revision_bytes"]:
            externo = not es_interna(e["destino_ip"], cfg)
            if origen in sensibles and externo:
                coincide.append(100041)
                cambio = _cambio_vigente(e, cambios)
                if cambio and cambio["activo"] == origen:
                    coincide.append(100042)
                    contexto.append(f"Ocurre durante {cambio['cambio_id']}, cuyo límite es: "
                                    f"«{cambio['limite']}»")
            else:
                coincide.append(100040)
            contexto.append(f"{e['bytes'] / 1e6:.0f} MB observados; no confirma extracción de información")

        # --- Calidad de las reglas registradas ------------------------------------
        if e["regla_id"] == "R01" and not (destino == "WEB-LAB" and e["puerto_destino"] == 443
                                           and e["accion"] == "allow"):
            coincide.append(100050)
            contexto.append(f"Registrado como R01 pero el flujo es {origen} -> {destino}:{e['puerto_destino']}")
        if e["regla_id"] == "R02" and e["accion"] == "allow":
            coincide.append(100060)

        if not coincide:
            coincide.append(100001 if e["accion"] == "allow" else 100010)

        principal = max(coincide, key=lambda r: (REGLAS[r][0], r))
        nivel, descripcion, grupos, mitre = REGLAS[principal]
        agente = destino if e["tipo"] == "autenticacion" else "FW-LAB"
        registro = {
            "evento_id": e["evento_id"],
            "fecha_hora": e["fecha_hora"],
            "timestamp": dt.isoformat() + "-05:00",
            "regla_id": principal,
            "nivel": nivel,
            "severidad": severidad(nivel, cfg),
            "descripcion": descripcion,
            "grupos": grupos,
            "mitre": mitre,
            "coincidencias": [f"{r}:{REGLAS[r][0]}" for r in sorted(set(coincide))],
            "agente": agente,
            "agente_ip": ip_por_nombre.get(agente, ""),
            "srcip": e["origen_ip"],
            "origen_activo": origen,
            "dstip": e["destino_ip"],
            "destino_activo": destino,
            "puerto": e["puerto_destino"],
            "accion": e["accion"],
            "regla_fw": e["regla_id"],
            "usuario": e["usuario_prueba"],
            "resultado": e["resultado"],
            "bytes": e["bytes"],
            "contexto": " | ".join(contexto),
        }
        (alertas if nivel >= cfg["log_alert_level"] else archivados).append(registro)

    for i, a in enumerate(alertas, 1):
        a["alerta_id"] = f"W{i:04}"
    return alertas, archivados


def correlacionar(alertas: list[dict], cfg: dict) -> list[dict]:
    """Agrupa alertas en casos para revisión: mismo activo sensible (o mismo par
    origen-destino) con menos de `correlacion_minutos` entre alertas consecutivas.
    Un caso es una hipótesis para revisar, no un incidente confirmado."""
    hueco = timedelta(minutes=cfg["correlacion_minutos"])
    sensibles = set(cfg["activos_sensibles"])
    abiertos: dict[str, dict] = {}
    casos: list[dict] = []
    for a in sorted(alertas, key=lambda x: (x["timestamp"], x["alerta_id"])):
        if a["destino_activo"] in sensibles:
            clave = a["destino_activo"]
        elif a["origen_activo"] in sensibles:
            clave = a["origen_activo"]
        else:
            clave = f"{a['origen_activo']}->{a['destino_activo']}"
        dt = datetime.fromisoformat(a["fecha_hora"])
        caso = abiertos.get(clave)
        if caso is None or dt - caso["_ultimo"] > hueco:
            caso = {"caso_id": f"C{len(casos) + 1:02}", "activo_clave": clave, "alertas": [],
                    "inicio": a["fecha_hora"], "_ultimo": dt}
            casos.append(caso)
            abiertos[clave] = caso
        caso["alertas"].append(a)
        caso["_ultimo"] = dt
        caso["fin"] = a["fecha_hora"]
        a["caso_id"] = caso["caso_id"]

    resumen = []
    for c in casos:
        nivel = max(a["nivel"] for a in c["alertas"])
        resumen.append({
            "caso_id": c["caso_id"],
            "activo_clave": c["activo_clave"],
            "inicio": c["inicio"],
            "fin": c["fin"],
            "n_alertas": len(c["alertas"]),
            "nivel_max": nivel,
            "severidad": severidad(nivel, cfg),
            "origenes": ", ".join(sorted({a["origen_activo"] for a in c["alertas"]})),
            "reglas": ", ".join(str(r) for r in sorted({a["regla_id"] for a in c["alertas"]})),
            "eventos": ", ".join(a["evento_id"] for a in c["alertas"]),
            "estado": "Pendiente de revisión humana",
        })
    return resumen
