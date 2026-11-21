# Procedimiento propuesto
Responsable por rol: Analista de monitoreo (revisión y primera disposición). Dueño del activo según el inventario (contexto y cierre). Seguridad (casos altos).

Frecuencia de revisión:
- Alertas altas: al recibir el aviso por Telegram o correo, en menos de 30 minutos en horario laboral.
- Alertas medias: en cada correo agrupado (cada 30 minutos).
- Alertas bajas y resumen diario: una vez al día, al inicio de la jornada.
- Puntajes de la IA: revisión semanal de las anomalías sin regla asociada.

Fuentes:
- Eventos de los agentes Wazuh y del firewall.
- Inventario de activos.
- Registro de cambios autorizados.
- Políticas del firewall.
- Configuración de servidores.

Controles de calidad:
- Cada evento recibe una sola alerta, con la regla de mayor nivel. Las demás reglas que coinciden quedan como coincidencias.
- Se verifica que la regla registrada corresponda al flujo (regla 100050).
- Relojes sincronizados con NTP.
- Las 14 pruebas automáticas se ejecutan después de cada cambio de reglas o umbrales.

Reglas y umbrales:
- 5 fallos en 10 minutos (mismo origen, destino y usuario): media.
- Éxito después de esos fallos: alta.
- 5 bloqueos en 10 minutos hacia un activo sensible, a 2 o más puertos: media.
- 50 MB o más desde un activo sensible hacia fuera: alta.
- Acceso fuera del horario 07:00-19:00: media. Si coincide con un cambio autorizado: baja.
- IA: puntaje menor que −0,15 es media; menor que −0,25 es alta.
- Todos los umbrales se ajustan en `pipeline/config_mvp.json`.

Cómo correlacionar: Agrupar las alertas del mismo activo sensible (o del mismo par origen-destino) que estén a menos de 30 minutos entre sí. Un caso se analiza como una unidad y no se cuenta cada alerta como un incidente.

Cuándo solicitar contexto:
- Siempre que una alerta alta afecte a DB-LAB o BACKUP-LAB.
- Cuando una actividad fuera de horario no coincida exactamente con un cambio autorizado (activo, origen, usuario y ventana).
- Cuando una anomalía de la IA no tenga una regla que la explique.

Criterio de cierre o escalamiento:
- Cerrar con justificación si la actividad coincide con un cambio autorizado y no excede su límite.
- Escalar si excede el límite, involucra un activo de criticidad alta o falta la evidencia para descartarla.
- Una alerta bloqueada por el firewall no se escala sola: se revisa la exposición.

Registro de decisiones: `entregables/Registro_alertas.csv`, con disposición, justificación y rol responsable. Los casos que se escalan llevan una ficha de incidente.

Revisión periódica:
- Mensual: revisar umbrales, falsos positivos y excepciones del firewall con vencimiento.
- Trimestral: reentrenar el modelo de IA con un periodo validado como normal.
