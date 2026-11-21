# Revisión de posible incidente
Fecha de apertura: 2026-11-20 02:10 (simulada a partir del archivo de eventos)

Alerta origen: W0004, regla 100042, nivel 14 (alta). Caso C01 en BACKUP-LAB. La refuerza IA002 (Isolation Forest, puntaje −0,28).

Hechos observados:
- E0324: BACKUP-LAB (10.60.30.10) envió 85 000 000 bytes a 198.51.100.200, TCP/443, con acción allow.
- El evento quedó registrado con la regla R01, que solo describe Internet → WEB-LAB TCP/443. El registro no corresponde al flujo.
- Ocurrió a las 02:10, fuera del horario de prueba (07:00-19:00) y dentro de la ventana de CH01 (02:00-02:30).
- CH01 autoriza la revisión de la copia desde ADMIN-LAB, con el límite «No autoriza envío externo de datos».

Cronología:
- 02:00, 02:01 y 02:02: admin_prueba entra por SSH desde ADMIN-LAB a BACKUP-LAB (E0321-E0323). Coincide con CH01.
- 02:10: salida de 85 MB desde BACKUP-LAB hacia 198.51.100.200 (E0324).
- Después no hay más eventos de BACKUP-LAB en el archivo.

Activos relacionados: BACKUP-LAB (criticidad alta, Respaldo), ADMIN-LAB (Gestión), FW-LAB (registro de la regla).

Hipótesis y evidencia faltante:
1. Copia externa legítima no documentada en CH01. Falta: lista de destinos de copia aprobados y la configuración del software de respaldo.
2. Error del administrador durante la revisión. Falta: registro de comandos de la sesión de admin_prueba, que hoy no se centraliza para este flujo.
3. Envío no autorizado de datos. Falta: el contenido o tipo de archivo, la reputación y el propietario de 198.51.100.200, y el registro de la regla que realmente aplicó en FW-LAB.

Con los archivos disponibles no se puede distinguir entre estas hipótesis.

Acciones propuestas (no ejecutadas):
- Pedir al responsable de Infraestructura la explicación del flujo y el registro de la sesión.
- Pedir a Redes el registro original de FW-LAB para la conexión de las 02:10.
- Si no hay justificación: restringir la salida de BACKUP-LAB (plan de hardening N01) y revisar la integridad de las copias.

Escalamiento por rol: Analista de monitoreo → Responsable de Infraestructura (dueño de BACKUP-LAB) → Seguridad. Si se confirma un envío no autorizado, escalar a la Dirección de Tecnología.

Decisión de cierre o continuidad: Continúa abierto. No se puede cerrar porque CH01 excluye de forma explícita los envíos externos. Se cierra solo con la evidencia de que el destino es un sitio de copia aprobado, documentando el ajuste en CH01.
