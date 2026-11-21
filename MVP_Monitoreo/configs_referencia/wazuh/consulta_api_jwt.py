"""REFERENCIA: flujo de autenticación JWT contra la API de Wazuh (puerto 55000).

1. POST /security/user/authenticate con usuario y contraseña  -> token firmado
2. Consultas con la cabecera  Authorization: Bearer <token>
3. El token vence (900 s por defecto); se pide uno nuevo al recibir 401.

Nota: la API del servidor Wazuh 4.x NO tiene un endpoint para listar alertas.
Sirve para agentes, reglas y estado del manager. Las alertas se leen de
/var/ossec/logs/alerts/alerts.json (inputs.tail de Telegraf) o del Wazuh indexer.

Requiere: pip install requests
Uso: WAZUH_API_URL=https://10.60.0.30:55000 WAZUH_API_USER=... WAZUH_API_PASSWORD=... \
     python consulta_api_jwt.py
"""
import os

import requests

URL = os.environ["WAZUH_API_URL"]
CA = os.environ.get("SSL_CA_CERT", True)   # ruta al certificado de la CA interna


def obtener_token() -> str:
    r = requests.post(f"{URL}/security/user/authenticate?raw=true",
                      auth=(os.environ["WAZUH_API_USER"], os.environ["WAZUH_API_PASSWORD"]),
                      verify=CA, timeout=10)
    r.raise_for_status()
    return r.text.strip()


class ClienteWazuh:
    def __init__(self):
        self.token = obtener_token()

    def get(self, ruta: str, **params) -> dict:
        for _ in range(2):
            r = requests.get(f"{URL}{ruta}", params=params, verify=CA, timeout=10,
                             headers={"Authorization": f"Bearer {self.token}"})
            if r.status_code == 401:          # token vencido: pedir otro una vez
                self.token = obtener_token()
                continue
            r.raise_for_status()
            return r.json()
        raise RuntimeError("No fue posible autenticarse con la API de Wazuh")


if __name__ == "__main__":
    api = ClienteWazuh()
    print(api.get("/agents/summary/status"))                       # agentes activos/desconectados
    print(api.get("/agents", status="disconnected", select="id,name,ip"))
