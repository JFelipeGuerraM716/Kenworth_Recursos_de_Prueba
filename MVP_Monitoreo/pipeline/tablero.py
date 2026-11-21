"""Genera un tablero HTML autocontenido que reproduce los paneles de Grafana de la propuesta.

No usa internet ni librerías externas: los gráficos son SVG generados aquí.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime
from html import escape

COLOR = {"baja": "#7a8ca3", "media": "#e0a100", "alta": "#d64545", "normal": "#9aa5b1"}
ORDEN = ["baja", "media", "alta"]


def _barras_horizontales(filas: list[tuple[str, dict[str, int]]], ancho=560, alto_fila=26) -> str:
    """filas: [(etiqueta, {severidad: conteo})] -> barras apiladas."""
    if not filas:
        return "<p class='vacio'>Sin datos</p>"
    maximo = max(sum(d.values()) for _, d in filas) or 1
    x0, util = 190, ancho - 190 - 40
    alto = alto_fila * len(filas) + 10
    partes = [f"<svg viewBox='0 0 {ancho} {alto}' role='img'>"]
    for i, (etiqueta, datos) in enumerate(filas):
        y = 5 + i * alto_fila
        partes.append(f"<text x='{x0 - 8}' y='{y + 15}' text-anchor='end' class='eti'>{escape(etiqueta)}</text>")
        x = x0
        for sev in ORDEN + ["normal"]:
            n = datos.get(sev, 0)
            if not n:
                continue
            w = util * n / maximo
            partes.append(f"<rect x='{x:.1f}' y='{y + 3}' width='{w:.1f}' height='{alto_fila - 8}' "
                          f"rx='3' fill='{COLOR[sev]}'><title>{sev}: {n}</title></rect>")
            x += w
        partes.append(f"<text x='{x + 6:.1f}' y='{y + 15}' class='num'>{sum(datos.values())}</text>")
    partes.append("</svg>")
    return "".join(partes)


def _alertas_por_hora(alertas: list[dict], ancho=560, alto=220) -> str:
    por_hora: dict[int, Counter] = defaultdict(Counter)
    for a in alertas:
        por_hora[int(a["fecha_hora"][11:13])][a["severidad"]] += 1
    maximo = max((sum(c.values()) for c in por_hora.values()), default=1)
    x0, y0, util_w, util_h = 36, alto - 28, ancho - 50, alto - 50
    paso = util_w / 24
    partes = [f"<svg viewBox='0 0 {ancho} {alto}' role='img'>",
              f"<line x1='{x0}' y1='{y0}' x2='{x0 + util_w}' y2='{y0}' class='eje'/>"]
    for marca in range(0, maximo + 1, max(1, maximo // 4)):
        y = y0 - util_h * marca / maximo
        partes.append(f"<text x='{x0 - 6}' y='{y + 4:.1f}' text-anchor='end' class='num'>{marca}</text>"
                      f"<line x1='{x0}' y1='{y:.1f}' x2='{x0 + util_w}' y2='{y:.1f}' class='guia'/>")
    for h in range(24):
        x = x0 + h * paso
        if h % 3 == 0:
            partes.append(f"<text x='{x + paso / 2:.1f}' y='{y0 + 16}' text-anchor='middle' class='num'>{h:02}h</text>")
        y = y0
        for sev in ORDEN:
            n = por_hora[h][sev]
            if n:
                hgt = util_h * n / maximo
                y -= hgt
                partes.append(f"<rect x='{x + 2:.1f}' y='{y:.1f}' width='{paso - 4:.1f}' height='{hgt:.1f}' "
                              f"fill='{COLOR[sev]}'><title>{h:02}h {sev}: {n}</title></rect>")
    partes.append("</svg>")
    return "".join(partes)


def _puntajes(ventanas: list[dict], cfg: dict, ancho=1140, alto=260) -> str:
    validas = [v for v in ventanas if v.get("puntaje") != ""]
    if not validas:
        return "<p class='vacio'>Modelo no disponible (instalar scikit-learn)</p>"
    pmin = min(min(v["puntaje"] for v in validas), cfg["ia"]["umbral_alta"]) - 0.05
    pmax = max(v["puntaje"] for v in validas) + 0.05
    x0, y0, util_w, util_h = 130, 20, ancho - 150, alto - 50

    def X(v):
        dt = datetime.fromisoformat(v["ventana_inicio"])
        return x0 + util_w * (dt.hour * 60 + dt.minute) / 1440

    def Y(p):
        return y0 + util_h * (pmax - p) / (pmax - pmin)

    partes = [f"<svg viewBox='0 0 {ancho} {alto}' role='img'>",
              f"<line x1='{x0}' y1='{y0 + util_h}' x2='{x0 + util_w}' y2='{y0 + util_h}' class='eje'/>"]
    for h in range(0, 25, 2):
        x = x0 + util_w * h / 24
        partes.append(f"<text x='{x:.1f}' y='{y0 + util_h + 16}' text-anchor='middle' class='num'>{h:02}h</text>")
    for nombre, umbral in (("media", cfg["ia"]["umbral_media"]), ("alta", cfg["ia"]["umbral_alta"])):
        y = Y(umbral)
        partes.append(f"<line x1='{x0}' y1='{y:.1f}' x2='{x0 + util_w}' y2='{y:.1f}' stroke='{COLOR[nombre]}' "
                      f"stroke-dasharray='5 4'/><text x='{x0 + util_w}' y='{y - 4:.1f}' text-anchor='end' "
                      f"class='num'>umbral {nombre} ({umbral})</text>")
    etiquetas: list[tuple[float, float]] = []
    for v in validas:
        sev = v["severidad_ia"]
        r = 5 if sev != "normal" else 3
        partes.append(f"<circle cx='{X(v):.1f}' cy='{Y(v['puntaje']):.1f}' r='{r}' fill='{COLOR[sev]}' "
                      f"opacity='{1 if sev != 'normal' else 0.55}'><title>{escape(v['origen_activo'])} "
                      f"{v['ventana_inicio'][11:16]} puntaje {v['puntaje']}</title></circle>")
        if sev == "alta":
            x, y = X(v), Y(v["puntaje"])
            vecino = any(o is not v and o["severidad_ia"] == "alta" and 0 < X(o) - x < 200
                         and abs(Y(o["puntaje"]) - y) < 25 for o in validas)
            lx, ly, ancla = (x - 8, y + 4, "end") if vecino else (x + 8, y + 4, "start")
            while any(abs(lx - ex) < 170 and abs(ly - ey) < 14 for ex, ey in etiquetas):
                ly -= 15
            etiquetas.append((lx, ly))
            partes.append(f"<text x='{lx:.1f}' y='{ly:.1f}' text-anchor='{ancla}' class='eti'>"
                          f"{escape(v['origen_activo'])} {v['ventana_inicio'][11:16]}</text>")
    partes.append(f"<text x='{x0 - 8}' y='{y0 + 8}' text-anchor='end' class='num'>{pmax:.2f}</text>"
                  f"<text x='{x0 - 8}' y='{y0 + util_h}' text-anchor='end' class='num'>{pmin:.2f}</text></svg>")
    return "".join(partes)


def _tabla(filas: list[dict], columnas: list[tuple[str, str]]) -> str:
    cab = "".join(f"<th>{escape(t)}</th>" for _, t in columnas)
    cuerpo = []
    for f in filas:
        celdas = []
        for clave, _ in columnas:
            valor = f.get(clave, "")
            if clave == "severidad" or clave == "severidad_ia":
                celdas.append(f"<td><span class='chip {valor}'>{escape(str(valor))}</span></td>")
            else:
                celdas.append(f"<td>{escape(str(valor))}</td>")
        cuerpo.append("<tr>" + "".join(celdas) + "</tr>")
    return f"<table><thead><tr>{cab}</tr></thead><tbody>{''.join(cuerpo)}</tbody></table>"


def generar(ruta, eventos, alertas, casos, ventanas, alertas_ia, envios, cfg) -> None:
    sev = Counter(a["severidad"] for a in alertas)
    equipos: dict[str, Counter] = defaultdict(Counter)
    for a in alertas:
        if not a["destino_activo"].startswith("externo:"):
            equipos[a["destino_activo"]][a["severidad"]] += 1
    intentos: dict[str, Counter] = defaultdict(Counter)
    for e in eventos:
        if e["resultado"] == "fallo" or e["accion"] == "deny":
            intentos[e["origen_ip"]]["media" if e["resultado"] == "fallo" else "baja"] += 1
    reglas: dict[str, Counter] = defaultdict(Counter)
    for a in alertas:
        reglas[f"{a['regla_id']} · nivel {a['nivel']}"][a["severidad"]] += 1

    def top(d):
        return sorted(d.items(), key=lambda kv: -sum(kv[1].values()))[:8]

    leyenda = "".join(f"<span><i style='background:{COLOR[s]}'></i>{s}</span>" for s in ORDEN)
    importantes = [a for a in alertas if a["severidad"] != "baja"] + alertas_ia
    importantes.sort(key=lambda a: (a["fecha_hora"], a["alerta_id"]))
    kpis = [("Eventos analizados", len(eventos)), ("Alertas (nivel ≥ 3)", len(alertas)),
            ("Altas", sev["alta"]), ("Medias", sev["media"]), ("Bajas", sev["baja"]),
            ("Casos para revisar", len(casos)), ("Anomalías IA", len(alertas_ia))]
    html = f"""<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Kenworth LAB · Tablero de monitoreo (prototipo)</title>
<style>
:root{{--bg:#f4f5f7;--card:#fff;--txt:#1f2933;--sub:#52606d;--borde:#dde2e8}}
@media (prefers-color-scheme:dark){{:root{{--bg:#111418;--card:#1b1f24;--txt:#e4e7eb;--sub:#9aa5b1;--borde:#2c333b}}}}
*{{box-sizing:border-box}}body{{margin:0;font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;background:var(--bg);color:var(--txt)}}
header{{padding:20px 28px 8px}}h1{{font-size:22px;margin:0 0 4px;font-weight:600}}header p{{margin:0;color:var(--sub);font-size:14px}}
main{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px;padding:16px 28px 32px}}
.card{{background:var(--card);border:1px solid var(--borde);border-radius:10px;padding:14px 16px}}
.card h2{{font-size:15px;margin:0 0 10px;font-weight:600}}.full{{grid-column:1/-1}}
.kpis{{display:grid;grid-template-columns:repeat(7,1fr);gap:12px}}.kpi{{text-align:center}}
.kpi b{{display:block;font-size:28px;font-weight:600}}.kpi span{{font-size:12px;color:var(--sub)}}
svg{{width:100%;height:auto;display:block}}.eti{{font-size:12px;fill:var(--txt)}}.num{{font-size:11px;fill:var(--sub)}}
.eje{{stroke:var(--sub);stroke-width:1}}.guia{{stroke:var(--borde);stroke-width:1}}
.leyenda{{display:flex;gap:14px;font-size:12px;color:var(--sub);margin:-4px 0 8px}}.leyenda i{{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:5px}}
table{{width:100%;border-collapse:collapse;font-size:12.5px}}th,td{{text-align:left;padding:6px 8px;border-bottom:1px solid var(--borde);vertical-align:top}}
th{{color:var(--sub);font-weight:600}}.chip{{padding:2px 8px;border-radius:10px;font-size:11px;color:#fff}}
.chip.alta{{background:{COLOR['alta']}}}.chip.media{{background:{COLOR['media']};color:#3b2a00}}.chip.baja{{background:{COLOR['baja']}}}
.nota{{font-size:12px;color:var(--sub);margin-top:8px}}
@media (max-width:900px){{main{{grid-template-columns:1fr}}.kpis{{grid-template-columns:repeat(3,1fr)}}}}
</style></head><body>
<header><h1>Kenworth LAB · Monitoreo de eventos</h1>
<p>Prototipo offline de la cadena Wazuh → Telegraf → InfluxDB → Grafana + IA local. Datos de prueba del 2026-11-20.
Una alerta o un caso no es un incidente confirmado: requiere revisión humana.</p></header>
<main>
<section class="card full"><div class="kpis">{''.join(f"<div class='kpi'><b>{v}</b><span>{escape(t)}</span></div>" for t, v in kpis)}</div></section>
<section class="card"><h2>Alertas por hora</h2><div class="leyenda">{leyenda}</div>{_alertas_por_hora(alertas)}</section>
<section class="card"><h2>Equipos más atacados (alertas por activo destino)</h2><div class="leyenda">{leyenda}</div>{_barras_horizontales(top(equipos))}</section>
<section class="card"><h2>Intentos fallidos y bloqueos por IP de origen</h2><div class="leyenda"><span><i style='background:{COLOR['media']}'></i>fallos de autenticación</span><span><i style='background:{COLOR['baja']}'></i>conexiones bloqueadas</span></div>{_barras_horizontales(top(intentos))}</section>
<section class="card"><h2>Top de reglas disparadas</h2><div class="leyenda">{leyenda}</div>{_barras_horizontales(top(reglas))}</section>
<section class="card full"><h2>Puntaje de anomalía (Isolation Forest, ventanas de {cfg['ia']['ventana_minutos']} min por IP de origen)</h2>{_puntajes(ventanas, cfg)}
<p class="nota">Más negativo = más raro. El modelo no conoce los cambios autorizados: una anomalía también puede ser una tarea legítima.</p></section>
<section class="card full"><h2>Casos correlacionados para revisión</h2>{_tabla(casos, [("caso_id", "Caso"), ("severidad", "Severidad"), ("activo_clave", "Activo"), ("inicio", "Inicio"), ("fin", "Fin"), ("origenes", "Orígenes"), ("n_alertas", "Alertas"), ("reglas", "Reglas"), ("estado", "Estado")])}</section>
<section class="card full"><h2>Alertas medias y altas (reglas + IA)</h2>{_tabla(importantes, [("alerta_id", "ID"), ("fecha_hora", "Fecha y hora"), ("severidad", "Severidad"), ("regla_id", "Regla"), ("descripcion", "Descripción"), ("origen_activo", "Origen"), ("destino_activo", "Destino"), ("contexto", "Evidencia y contexto")])}</section>
<section class="card full"><h2>Notificaciones enviadas (simuladas)</h2>{_tabla(envios, [("envio", "Envío"), ("canal", "Canal"), ("severidad", "Severidad"), ("n_alertas", "Alertas"), ("asunto", "Asunto")])}
<p class="nota">Altas: Telegram + correo inmediato. Medias: correo agrupado cada {cfg['notificaciones']['agrupar_medias_minutos']} min. Bajas: solo tablero y resumen diario.</p></section>
</main></body></html>"""
    ruta.write_text(html, encoding="utf-8")
