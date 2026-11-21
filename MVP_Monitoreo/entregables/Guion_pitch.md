# Presentación de 3 a 5 minutos

## 1. Problema y usuario (40 s)
El analista de monitoreo recibe 324 eventos en un día y no sabe cuáles mirar primero. Nuestro MVP los convierte en 24 alertas clasificadas, 3 casos para revisar y solo 6 avisos inmediatos.

Arquitectura propuesta: agentes Wazuh → manager (nivel 0-15) → Telegraf → InfluxDB → Grafana, con notificaciones por Telegram y correo y una IA local que detecta lo inusual sin enviar datos a la nube.

## 2. Demostración con un caso (90 s)
Abrir `salidas/tablero.html`:
- El panel «Alertas por hora» muestra un pico a las 02:00, fuera de horario.
- En la tabla de casos, C01 (BACKUP-LAB) aparece como alta.
- W0004: a las 02:10 salieron 85 MB hacia un destino externo. El evento quedó registrado como R01, que no corresponde.
- La evidencia adicional es CH01, que autoriza la revisión de 02:00 a 02:30 pero dice «No autoriza envío externo de datos».
- Los accesos de las 02:00 coinciden con CH01 y quedan como bajos, sin aviso. El envío externo llega por Telegram.
- La IA marcó la misma ventana de forma independiente (puntaje −0,28).

## 3. Evidencia y prioridades (60 s)
Prioridad = impacto × exposición:
1. R02 permite Usuarios → DB-LAB con cualquier servicio y sin registro (9, alta). Por ahí pasaron 7 fallos y un éxito por SSH.
2. La salida de BACKUP-LAB no tiene restricción (9, alta).
3. DB-LAB no tiene MFA y usa cuentas compartidas (6, alta).

## 4. Prueba realizada y mejora (40 s)
- 14 pruebas automáticas pasan: umbral exacto de 5 fallos, 4 fallos sin alerta, fuera de ventana, frontera de 10 minutos, CH01, una alerta por evento y la IA reproducible.
- Detectamos las 6 alertas de referencia del paquete y agregamos el éxito tras fallos y el reconocimiento bloqueado.
- Mejora detectada: la IA también marcó la actividad autorizada. Falta darle al modelo la lista de cambios autorizados.

## 5. Límites y preguntas para la empresa (30 s)
- Son datos de prueba de un solo día. Una alerta no es un incidente, y C01 no demuestra que se hayan extraído datos.
- Preguntas para la empresa: ¿hay destinos de copia externos aprobados? ¿Quién usa R02 y para qué? ¿Qué retención de registros tienen?

Aclaración: todos los datos y resultados son de prueba. No describen la infraestructura de Kenworth.
