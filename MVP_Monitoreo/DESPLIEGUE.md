# Guía de despliegue en tu propio equipo (Windows + WSL2 Ubuntu)

Esta guía monta la arquitectura completa en **tu computador personal**:

> Wazuh manager → Telegraf → InfluxDB → Grafana (Nginx 443) + IA local, con alertas por Telegram y correo.

**Importante:** solo debe desplegarse en tu propio equipo o en un laboratorio autorizado. No instales agentes ni hagas pruebas en la red del ITM, de EAFIT ni de Kenworth.

El despliegue tiene dos etapas:
- **Etapa A (partes 1 a 5):** stack de monitoreo y modo demostración con los datos del reto. No necesita Wazuh.
- **Etapa B (partes 6 a 8):** Wazuh manager real, un agente en Windows y entrenamiento de la IA.

## Requisitos
- Windows 10 u 11 con WSL2 y Ubuntu 22.04 o 24.04.
- 8 GB de RAM y 15 GB libres en disco.
- Conexión a internet para descargar imágenes y paquetes.
- Una cuenta de Telegram y una cuenta de Gmail con verificación en dos pasos.

Todos los comandos de esta guía se escriben en la terminal de Ubuntu (WSL), salvo los que dicen **PowerShell**.

---

## Parte 1. Preparar WSL

**1.1** Activa systemd en WSL:
```bash
sudo tee /etc/wsl.conf > /dev/null <<'EOF'
[boot]
systemd=true
EOF
```

**1.2** En **PowerShell**, reinicia WSL:
```powershell
wsl --shutdown
```

**1.3** Abre de nuevo Ubuntu y comprueba que systemd está activo:
```bash
systemctl is-system-running
```
La respuesta debe ser `running` o `degraded`.

**1.4** Instala Docker Engine con el script oficial:
```bash
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
```

**1.5** Cierra la terminal de Ubuntu, ábrela de nuevo y comprueba Docker:
```bash
docker run --rm hello-world
docker compose version
```

---

## Parte 2. Descargar el proyecto

**2.1** Entra a la carpeta del repositorio y cambia a la rama del MVP:
```bash
cd /mnt/c/Users/User/Downloads/6/Kenworth_Recursos_de_Prueba
git fetch origin
git checkout mvp-monitoreo
git pull
```

**2.2** Copia la carpeta de configuración al sistema de archivos de Linux. Docker funciona mejor ahí que en `/mnt/c`:
```bash
mkdir -p ~/kenworth
cp -r MVP_Monitoreo ~/kenworth/
cd ~/kenworth/MVP_Monitoreo/configs_referencia
```
Desde aquí, todos los comandos se ejecutan en `~/kenworth/MVP_Monitoreo/configs_referencia`.

---

## Parte 3. Configurar

**3.1** Crea el archivo de variables:
```bash
cp .env.example .env
```

**3.2** Genera contraseñas y el token de administrador de InfluxDB, y escríbelos en `.env`:
```bash
sed -i "s|^INFLUX_ADMIN_PASSWORD=.*|INFLUX_ADMIN_PASSWORD=$(openssl rand -hex 16)|" .env
sed -i "s|^INFLUX_ADMIN_TOKEN=.*|INFLUX_ADMIN_TOKEN=$(openssl rand -hex 32)|" .env
sed -i "s|^GRAFANA_ADMIN_PASSWORD=.*|GRAFANA_ADMIN_PASSWORD=$(openssl rand -hex 12)|" .env
```

**3.3** Crea el bot de Telegram:
1. En Telegram, abre **@BotFather** y envía `/newbot`.
2. Escribe un nombre y un usuario terminado en `bot` (por ejemplo `kenworth_lab_alertas_bot`).
3. Copia el token que te entrega.
4. Abre el chat con tu bot y envíale el mensaje `hola`.
5. En el navegador abre `https://api.telegram.org/bot<TOKEN>/getUpdates`, cambiando `<TOKEN>` por el token del bot.
6. Busca `"chat":{"id":` y copia el número que aparece.

**3.4** Crea la contraseña de aplicación de Gmail:
1. Entra a https://myaccount.google.com/apppasswords
2. Crea una contraseña con el nombre `Grafana`.
3. Copia los 16 caracteres sin espacios.

**3.5** Abre `.env` y completa estas líneas:
```bash
nano .env
```
```
SMTP_USER=tu-correo@gmail.com
SMTP_APP_PASSWORD=la-contraseña-de-16-caracteres
CORREO_ALERTAS=correo-que-recibe-las-alertas@gmail.com
TELEGRAM_BOT_TOKEN=el-token-de-BotFather
TELEGRAM_CHAT_ID=el-numero-del-chat
```
Guarda con `Ctrl+O` y `Enter`, y sal con `Ctrl+X`.

**3.6** Genera los certificados TLS:
```bash
bash scripts/generar_certs.sh
```
Quedan en la carpeta `certs/`.

---

## Parte 4. Levantar el stack

**4.1** Inicia InfluxDB y espera 20 segundos:
```bash
docker compose up -d influxdb
sleep 20
```

**4.2** Crea los tokens de InfluxDB para cada servicio:
```bash
bash scripts/crear_tokens.sh
```
Debe responder `Tokens creados y guardados en .env`.

**4.3** Inicia el resto de servicios:
```bash
docker compose up -d --build
```

**4.4** Comprueba que todos los servicios estén en marcha:
```bash
docker compose ps
```
Deben aparecer `influxdb`, `telegraf`, `grafana`, `nginx`, `ia` y `wazuh-token` con estado `running`. En la etapa A, `wazuh-token` reintenta cada 30 segundos porque todavía no hay Wazuh. Eso es normal.

**4.5** Crea los puntos de contacto (Telegram y correo) y la política de notificación:
```bash
sleep 20
bash scripts/configurar_notificaciones.sh
```
Debe terminar con `Notificaciones configuradas`.

**4.6** Consulta la contraseña de Grafana:
```bash
grep GRAFANA_ADMIN_PASSWORD .env
```

**4.7** En el navegador de Windows abre **https://localhost**. El navegador avisará que el certificado no es de confianza: elige **Avanzado → Continuar**. Inicia sesión con el usuario `admin` y la contraseña del paso 4.6.

**4.8** Ve a **Dashboards → Seguridad → Kenworth LAB · Monitoreo de seguridad**. Por ahora los paneles están vacíos.

---

## Parte 5. Probar con el modo demostración

El modo demostración reproduce las 24 alertas y los 299 puntajes de IA del reto con la hora actual. Telegraf los lee, los guarda en InfluxDB y Grafana los muestra y notifica.

**5.1** Inicia la reproducción. Un minuto de datos pasa en un segundo, así que dura unos 8 minutos:
```bash
python3 scripts/reproducir_demo.py --velocidad 60
```

**5.2** Mientras corre, revisa el resultado:
- **Grafana:** los paneles se llenan. En «Alertas altas» aparecen 2, en «Alertas medias» 8 y en «Alertas bajas» 14.
- **Telegram:** llegan mensajes por las alertas altas y por las anomalías altas de la IA.
- **Correo:** llegan las alertas altas y un correo agrupado con las medias.
- **Grafana → Alerting → Alert rules:** las reglas cambian a `Firing` mientras hay alertas recientes.

**5.3** Si quieres repetir la demostración, ejecuta de nuevo el paso 5.1.

---

## Parte 6. Instalar el Wazuh manager

**6.1** Agrega el repositorio oficial de Wazuh e instala el manager:
```bash
sudo apt-get install -y gnupg apt-transport-https
curl -s https://packages.wazuh.com/key/GPG-KEY-WAZUH | sudo gpg --no-default-keyring --keyring gnupg-ring:/usr/share/keyrings/wazuh.gpg --import
sudo chmod 644 /usr/share/keyrings/wazuh.gpg
echo "deb [signed-by=/usr/share/keyrings/wazuh.gpg] https://packages.wazuh.com/4.x/apt/ stable main" | sudo tee /etc/apt/sources.list.d/wazuh.list
sudo apt-get update
sudo apt-get install -y wazuh-manager
sudo systemctl enable --now wazuh-manager
```

**6.2** Copia las reglas personalizadas y la lista de cambios autorizados:
```bash
sudo cp wazuh/local_rules.xml /var/ossec/etc/rules/local_rules.xml
sudo cp wazuh/cambios_autorizados /var/ossec/etc/lists/cambios_autorizados
sudo chown wazuh:wazuh /var/ossec/etc/rules/local_rules.xml /var/ossec/etc/lists/cambios_autorizados
```

**6.3** Edita la configuración del manager:
```bash
sudo nano /var/ossec/etc/ossec.conf
```
- Dentro de `<global>`, agrega `<logall_json>yes</logall_json>`.
- Dentro de `<ruleset>`, agrega `<list>etc/lists/cambios_autorizados</list>`.

El archivo `wazuh/manager_ossec_fragmento.conf` muestra cómo quedan esas líneas.

**6.4** Verifica las reglas:
```bash
sudo /var/ossec/bin/wazuh-analysisd -t
```
No debe mostrar errores.

**6.5** Pon en la API de Wazuh el certificado firmado por tu CA:
```bash
sudo cp certs/wazuh-api.crt /var/ossec/api/configuration/ssl/server.crt
sudo cp certs/wazuh-api.key /var/ossec/api/configuration/ssl/server.key
sudo chown wazuh:wazuh /var/ossec/api/configuration/ssl/server.*
sudo chmod 400 /var/ossec/api/configuration/ssl/server.*
sudo systemctl restart wazuh-manager
```

**6.6** Escribe en `.env` el número del grupo `wazuh`:
```bash
sed -i "s|^WAZUH_GID=.*|WAZUH_GID=$(getent group wazuh | cut -d: -f3)|" .env
```

**6.7** Crea el usuario de solo lectura de la API. En una instalación nueva, el administrador es `wazuh` con contraseña `wazuh`:
```bash
WAZUH_ADMIN_USER=wazuh WAZUH_ADMIN_PASSWORD=wazuh bash scripts/crear_usuario_api.sh
```
Debe responder `Usuario telegraf-ro creado con el rol readonly`. Después cambia la contraseña del usuario `wazuh` siguiendo la sección «Securing the Wazuh server API» de la documentación oficial.

**6.8** Reinicia Telegraf y el servicio del token:
```bash
docker compose up -d --force-recreate telegraf wazuh-token
```

**6.9** Comprueba que el token se obtiene:
```bash
docker compose logs --tail 5 wazuh-token
```
No debe aparecer «No se pudo obtener el token».

---

## Parte 7. Conectar un agente (Windows)

**7.1** Consulta la versión del manager:
```bash
dpkg -l wazuh-manager | tail -1
```
Por ejemplo `4.9.2-1`.

**7.2** En **PowerShell como administrador**, descarga e instala el agente de la misma versión. Cambia `4.9.2` por tu versión:
```powershell
Invoke-WebRequest -Uri https://packages.wazuh.com/4.x/windows/wazuh-agent-4.9.2-1.msi -OutFile $env:TEMP\wazuh-agent.msi
msiexec.exe /i $env:TEMP\wazuh-agent.msi /q WAZUH_MANAGER="127.0.0.1" WAZUH_AGENT_NAME="PC-FELIPE"
NET START WazuhSvc
```

**7.3** En Ubuntu, comprueba que el agente aparece como activo:
```bash
sudo /var/ossec/bin/agent_control -l
```

**7.4** En Grafana, el panel «Agentes desconectados» debe mostrar `0`. Los eventos del agente empiezan a llegar a `wazuh_alertas` y `wazuh_eventos`.

---

## Parte 8. Entrenar la IA

**8.1** Deja el agente funcionando al menos un día con el uso normal del equipo.

**8.2** Entrena el modelo con ese periodo:
```bash
docker compose run --rm ia python ia_influx.py entrenar --dias 1
```
Debe responder `Modelo entrenado con N ventanas`.

**8.3** Reinicia el servicio de IA:
```bash
docker compose restart ia
```
Cada 5 minutos escribe el puntaje de anomalía en InfluxDB, y el panel «Puntaje de anomalía (IA local)» lo grafica. Repite el entrenamiento cuando tengas más días de datos normales (por ejemplo `--dias 7`).

---

## Verificación final

| Comprobación | Resultado esperado |
|---|---|
| `docker compose ps` | 6 servicios en `running` |
| https://localhost | Grafana abre por HTTPS |
| Tablero «Kenworth LAB · Monitoreo de seguridad» | 10 paneles con datos |
| Modo demostración | 2 altas, 8 medias y 14 bajas; mensajes en Telegram y correo |
| `sudo /var/ossec/bin/agent_control -l` | Agente `PC-FELIPE` activo |
| Grafana → Alerting → Contact points → **Test** | Llega un mensaje de prueba a Telegram y al correo |

## Solución de problemas

| Síntoma | Revisión |
|---|---|
| Telegraf no lee alertas | `docker compose logs telegraf`. Si dice `permission denied`, repite el paso 6.6 y el 6.8 |
| `crear_tokens.sh` falla | InfluxDB aún no terminó de iniciar: espera 30 segundos y repite el paso 4.2 |
| No llegan mensajes de Telegram | Revisa `TELEGRAM_CHAT_ID` y que le hayas escrito al bot primero; luego repite el paso 4.5 |
| No llegan correos | Revisa que la contraseña de aplicación no tenga espacios |
| El agente no se conecta | `Get-Content "C:\Program Files (x86)\ossec-agent\ossec.log" -Tail 20` en PowerShell |

## Apagar o borrar

Apagar el stack conservando los datos:
```bash
docker compose down
```
Borrar el stack y todos sus datos:
```bash
docker compose down -v
```
Detener el Wazuh manager:
```bash
sudo systemctl stop wazuh-manager
```
