# REFERENCIA: contenedor de la IA local (modo detección).
# Entrenar primero:  docker compose run --rm ia python ia_influx.py entrenar --dias 7
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY ia_influx.py .
RUN useradd --create-home ia && mkdir -p /modelo && chown ia /modelo
USER ia
CMD ["python", "ia_influx.py", "detectar"]
