# ──────────────────────────────────────────
# AudioToText Web — Dockerfile
# ──────────────────────────────────────────

FROM python:3.10-slim

# Instalar dependencias del sistema (ffmpeg)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Directorio de trabajo
WORKDIR /app

# Copiar requirements e instalar dependencias Python
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir flask werkzeug gunicorn openai-whisper numpy numba more-itertools tiktoken ffmpeg-python deepl openai

# Copiar código fuente
COPY . .

# Crear carpetas de datos
RUN mkdir -p uploads audio_transcription

# Puerto de la aplicación
EXPOSE 5000

# Variables de entorno por defecto
ENV FLASK_DEBUG=false
ENV PORT=5000

# Arrancar con gunicorn (producción)
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "600", "--worker-class", "sync", "app:app"]
