# Configuraciones de referencia

Estos archivos muestran cómo quedaría la arquitectura de la propuesta en un entorno real. **No se despliegan en el laboratorio**: el reto es offline y no autoriza conexiones a la red del campus ni de Kenworth. Antes de usarlos en un entorno autorizado, revíselos con los responsables de cada servicio.

## Cadena y puertos

| Componente | Puerto | Protección | Archivo |
|---|---|---|---|
| Agente Wazuh → manager (eventos) | 1514/TCP | Cifrado AES | `wazuh/agente_ossec_fragmento.conf` |
| Registro de agentes | 1515/TCP | Contraseña de registro | `wazuh/agente_ossec_fragmento.conf` |
| API REST del manager | 55000/TCP | HTTPS + JWT (900 s) | `wazuh/renovar_token.sh`, `wazuh/consulta_api_jwt.py` |
| Reglas personalizadas | — | — | `wazuh/local_rules.xml` |
| Telegraf → InfluxDB | 8086/TCP (interno) | TLS + token de escritura | `telegraf/telegraf.conf` |
| Grafana | 3000/TCP (interno) | Solo detrás del proxy | `grafana/provisioning/` |
| Nginx (publicación) | 443/TCP | TLS 1.2/1.3 | `nginx/grafana.conf` |
| IA local | — | Token propio; sin salida a internet | `ia/ia_influx.py` |

## Cómo se obtiene cada dato

- **Alertas**: Telegraf lee `/var/ossec/logs/alerts/alerts.json` con `inputs.tail`. La API del servidor Wazuh 4.x no tiene un endpoint para listar alertas, así que esta es la vía directa. La otra opción es consultar el Wazuh indexer en el puerto 9200.
- **Todos los eventos** (para la IA): `archives.json` con `logall_json` activado en el manager.
- **Estado de los agentes**: API en el puerto 55000 con JWT. El servicio `wazuh-token` pide el token con usuario y contraseña, lo guarda en un archivo y lo renueva antes de que venza. Telegraf lo envía en la cabecera `Authorization: Bearer <token>`.

## Severidad y notificaciones

| Nivel de regla | Severidad | Notificación |
|---|---|---|
| 0–6 | Baja | Ninguna; queda en el tablero y en el resumen diario |
| 7–11 | Media | Correo agrupado cada 30 minutos |
| 12–15 | Alta | Telegram y correo inmediatos |

La IA usa la misma ruta: un puntaje menor que −0,25 es alerta alta, y uno entre −0,25 y −0,15 es alerta media.

## Puesta en marcha (entorno autorizado)

1. Instalar el Wazuh manager en LOG-LAB según la documentación oficial y copiar `local_rules.xml`.
2. Crear en el manager un usuario de API de solo lectura para Telegraf.
3. Generar la CA interna y los certificados en `certs/`: `ca.crt`, `influxdb.crt/.key` y `grafana.crt/.key`.
4. Copiar `.env.example` como `.env` y completar los valores. El archivo `.env` no se sube al repositorio.
5. Crear el bot de Telegram con BotFather y obtener el chat ID. Para Gmail, crear una contraseña de aplicación.
6. Ejecutar `docker compose up -d`.
7. Entrenar la IA con un periodo normal: `docker compose run --rm ia python ia_influx.py entrenar --dias 7`.
8. Probar cada regla con `wazuh-logtest` y enviar una alerta de prueba desde Grafana a cada punto de contacto.
