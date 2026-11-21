# MVP: monitoreo con clasificación por severidad, notificaciones e IA local

Prototipo offline de la arquitectura **Wazuh → Telegraf → InfluxDB → Grafana + IA local (Isolation Forest)**, construido sobre los datos de prueba del reto Kenworth. Lee solo archivos del paquete, no se conecta a ninguna IP y no envía nada por internet.

## Equivalencia con la arquitectura real

| Arquitectura propuesta | En el prototipo |
|---|---|
| Agentes Wazuh envían eventos (1514/TCP, AES) | `02_Datos/eventos_normalizados.csv` |
| Wazuh manager: reglas y nivel 0–15 | `pipeline/reglas.py` (reglas 100001–100060) |
| `/var/ossec/logs/alerts/alerts.json` | `salidas/alerts.json` (mismo formato) |
| Telegraf escribe en InfluxDB (8086, TLS, token) | `salidas/influx_line_protocol.txt` |
| IA local con Isolation Forest | `pipeline/anomalias.py` → `salidas/anomalias_ia.csv` |
| Grafana Alerting: Telegram y correo | `pipeline/notificaciones.py` → `salidas/notificaciones/` |
| Paneles de Grafana | `salidas/tablero.html` |
| Configuración real (no desplegada) | `configs_referencia/` |

Severidad: **baja 0–6** (solo tablero y resumen diario), **media 7–11** (correo agrupado cada 30 minutos) y **alta 12–15** (Telegram y correo inmediatos).

## Requisitos
- Python 3.10 o superior.
- scikit-learn, solo para la capa de IA. Sin scikit-learn el resto de la cadena funciona y la IA aparece como «sin modelo».

## Cómo ejecutarlo

1. Abra una terminal en la carpeta principal del paquete (`Kenworth_Recursos_de_Prueba`).

2. Cree un entorno virtual e instale scikit-learn.

   En WSL o Linux:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install scikit-learn
   ```
   En Windows (PowerShell):
   ```powershell
   py -m venv .venv
   .venv\Scripts\Activate.ps1
   pip install scikit-learn
   ```

3. Ejecute la cadena completa:
   ```bash
   python MVP_Monitoreo/pipeline/run_mvp.py
   ```
   En pantalla aparece el resumen: eventos, alertas por severidad, casos, anomalías y notificaciones.

4. Abra el tablero `MVP_Monitoreo/salidas/tablero.html` en el navegador. Desde WSL:
   ```bash
   explorer.exe MVP_Monitoreo/salidas/tablero.html
   ```

5. Ejecute las pruebas:
   ```bash
   python -m unittest discover -s MVP_Monitoreo/pruebas -v
   ```
   Deben aparecer 14 pruebas con resultado `OK`.

6. Para cambiar umbrales (fallos, ventana, horario, volumen, umbrales de la IA), edite `MVP_Monitoreo/pipeline/config_mvp.json` y repita los pasos 3 y 5.

## Salidas

| Archivo | Contenido |
|---|---|
| `salidas/tablero.html` | Paneles: alertas por hora, equipos más atacados, intentos fallidos por IP, top de reglas, puntaje de anomalía, casos, alertas y notificaciones |
| `salidas/alertas_mvp.csv` | Una alerta por evento con nivel, severidad, reglas que coinciden y contexto |
| `salidas/casos.csv` | Alertas agrupadas por activo y cercanía en el tiempo |
| `salidas/anomalias_ia.csv` | Variables y puntaje de cada ventana de 10 minutos por IP de origen |
| `salidas/notificaciones.csv` y `salidas/notificaciones/*.txt` | Avisos simulados por canal |
| `salidas/alerts.json` | Alertas en formato Wazuh |
| `salidas/influx_line_protocol.txt` | Mediciones `wazuh_alertas` e `ia_anomalias` |
| `salidas/resumen_mvp.json` | Conteos generales |

## Resultados con los datos de prueba

- **324 eventos**: 300 son tráfico web previsto (nivel 2, archivado sin alerta) y 24 generan alerta.
- **Severidad**: 2 altas, 8 medias y 14 bajas.
- **3 casos** para revisión humana:
  - **C01 BACKUP-LAB (alta)**: accesos de las 02:00 cubiertos por CH01, seguidos de un envío de 85 MB a un destino externo a las 02:10. CH01 no autoriza envíos externos, y el evento quedó registrado con R01, que no corresponde.
  - **C02 DB-LAB (alta)**: 7 fallos de SSH de usr_prueba_07 desde PC-LAB-01 y un éxito a las 09:08, a través de la excepción R02.
  - **C03 DB-LAB (media)**: 12 conexiones bloqueadas desde 203.0.113.77 a los puertos 22, 5432 y 3389.
- **IA**: de 299 ventanas, las 4 más anómalas son exactamente las de los tres casos. El modelo no conoce los cambios autorizados, por eso también marca la sesión de CH01.
- **Notificaciones**: 6 por Telegram, 6 correos inmediatos, 2 correos agrupados y 1 resumen diario. Sin clasificar, cada una de las 29 alertas (24 de reglas y 5 de la IA) habría generado un aviso.
- Las 6 alertas de referencia de `07_Validacion` están cubiertas. AL004 y AL005 quedan como una sola alerta (W0004), porque corresponden al mismo evento.

## Límites
- Los datos son de prueba y de un solo día. Alertas y casos son hipótesis para revisión humana, no incidentes confirmados.
- Los umbrales de la IA (−0,15 y −0,25) se calibraron con este mismo día. Con datos reales hay que entrenar con un periodo validado como normal y recalibrar.
- Las reglas de `configs_referencia/wazuh/local_rules.xml` deben ajustarse a los decodificadores reales y probarse con `wazuh-logtest`.
- La API de Wazuh (55000) no entrega alertas. Las alertas se leen de `alerts.json` o del Wazuh indexer, y la API con JWT se usa para el estado de los agentes.
- No se evalúan vulnerabilidades: las actualizaciones pendientes no tienen versión ni CVE.

## Entregables del reto
Están en `entregables/`, a partir de las plantillas de `05_Plantillas`:
- Canvas del MVP
- Registro de alertas
- Plan y checklist de hardening
- Registro de pruebas
- Ficha de incidente (C01)
- Procedimiento de monitoreo
- Guion del pitch
- Preguntas para la empresa
