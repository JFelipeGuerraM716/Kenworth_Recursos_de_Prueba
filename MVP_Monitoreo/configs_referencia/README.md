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

## Puesta en marcha

Los pasos completos están en [`../DESPLIEGUE.md`](../DESPLIEGUE.md).

| Script | Para qué sirve |
|---|---|
| `scripts/generar_certs.sh` | Crea la CA interna y los certificados de InfluxDB, Grafana y la API de Wazuh |
| `scripts/crear_tokens.sh` | Crea un token de InfluxDB por servicio, con el mínimo permiso |
| `scripts/crear_usuario_api.sh` | Crea el usuario de solo lectura de la API de Wazuh |
| `scripts/reproducir_demo.py` | Modo demostración: reproduce las alertas del reto con la hora actual |
