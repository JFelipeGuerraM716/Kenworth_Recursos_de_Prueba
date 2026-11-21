# Equipo y alcance
Nombre: [completar]
Integrantes: [completar]

Usuario: Analista de monitoreo de la Dirección de Tecnología (rol de Seguridad), que revisa eventos todos los días y decide qué escalar.

Problema seleccionado: Los eventos de red y de autenticación llegan sin priorizar. El analista no sabe cuáles requieren atención inmediata, recibe ruido de actividad autorizada y no tiene una forma consistente de unir la alerta con su evidencia.

Función indispensable: Clasificar cada evento por severidad (baja, media o alta según un nivel de 0 a 15), agrupar las alertas en casos con su evidencia y notificar solo lo que requiere acción: las altas al instante, las medias agrupadas y las bajas en un resumen diario.

Fuentes de evidencia:
- `02_Datos/eventos_normalizados.csv` (324 eventos)
- `02_Datos/inventario_activos.csv` (IP, zona y criticidad)
- `02_Datos/cambios_autorizados.csv` (CH01)
- `03_Configuraciones/politicas_firewall_prueba.csv` (R01-R04)
- `03_Configuraciones/servidores_prueba.json` (MFA, registro, respaldo)

Arquitectura propuesta (real): agentes Wazuh → Wazuh manager (reglas, nivel 0-15) → Telegraf → InfluxDB → Grafana (paneles y alertas por Telegram y correo) + IA local con Isolation Forest.
Prototipo (laboratorio): la misma cadena simulada en Python con los archivos del paquete, sin red.

Qué no hace el MVP:
- No se conecta a ningún equipo ni escanea IP.
- No confirma incidentes, no atribuye atacantes y no demuestra extracción de información.
- No evalúa vulnerabilidades (sin versiones ni CVE).
- No despliega Wazuh, InfluxDB ni Grafana: las configuraciones son de referencia.
- La IA se entrenó con un solo día de datos de prueba, así que sus umbrales son provisionales.

Cómo se probará:
- Los cuatro casos controlados de `07_Validacion` (4 fallos, 5 fallos, fuera de ventana y frontera de 10 minutos).
- La actividad autorizada CH01 y el volumen externo E0324.
- El contraste con las 6 alertas de referencia del paquete.
- 14 pruebas automáticas.
- Otro equipo usa el tablero para encontrar la evidencia de W0004.
