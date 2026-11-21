# Preguntas pendientes

## Del paquete original
- ¿Cuáles son los activos críticos y sus responsables?
- ¿Qué mantenimiento está autorizado y dónde se registra?
- ¿Qué retención de logs y permisos de consulta se tienen?
- ¿Qué versiones y boletines aplican a las actualizaciones?
- ¿Cuándo se probó una restauración y cuál fue su resultado?
- ¿Cómo se aprueban excepciones del firewall?
- ¿Qué obligaciones de confidencialidad y uso de información debemos cumplir?

## Derivadas del MVP
- ¿Existen destinos de copia externa aprobados para BACKUP-LAB? ¿Es 198.51.100.200 uno de ellos? (caso C01)
- ¿Qué usuarios o aplicaciones necesitan R02 (Usuarios → DB-LAB any) y para qué servicio? (H01)
- ¿Quién es usr_prueba_07 y es normal que administre DB-LAB por SSH desde PC-LAB-01? (caso C02)
- ¿El registro del firewall indica la regla que realmente aplicó? ¿Por qué E0324 aparece como R01? (N02)
- ¿Cuál es el horario real de operación y qué tareas nocturnas son habituales? Se necesita para ajustar las reglas de horario y entrenar la IA.
- ¿Hay un periodo de operación que la empresa considere normal y que sirva para entrenar el modelo?
- ¿Se permite instalar agentes Wazuh en los servidores y qué consumo de recursos se acepta?
- ¿Qué canal de notificación está aprobado (Telegram, correo corporativo u otro) y quién debe recibir las alertas altas fuera de horario?
- ¿Existe un SIEM o una herramienta de monitoreo con la que esta propuesta deba integrarse?
