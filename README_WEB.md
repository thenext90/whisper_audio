# AudioToText Web — README
# ══════════════════════════════════════════════════════════

## 🎙️ AudioToText Web

Aplicación web para transcribir y traducir audio a texto usando
[OpenAI Whisper](https://github.com/openai/whisper).

Basada en [Carleslc/AudioToText](https://github.com/Carleslc/AudioToText).

---

## ✨ Características

- 🌐 Interfaz web moderna (dark mode)
- 📤 Carga de audio por clic o arrastrar y soltar
- 🤖 Modelos: tiny · base · small · medium · large-v1 · large-v2 · turbo
- 🌍 Más de 90 idiomas soportados
- 📄 Salida en: TXT · VTT · SRT · TSV · JSON
- 🕘 Historial de transcripciones
- 🐳 Docker listo para VPS

---

## 🚀 Instalación local

### Requisitos previos

- Python 3.10+
- [ffmpeg](https://ffmpeg.org/download.html)

```bash
# Ubuntu/Debian
sudo apt update && sudo apt install -y ffmpeg
```

### 1. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 2. Arrancar en desarrollo

```bash
python app.py
```

Abre [http://localhost:5000](http://localhost:5000)

---

## 🐳 Docker (local y VPS)

### Arrancar con Docker Compose

```bash
# Copiar configuración
cp .env.example .env

# Construir e iniciar
docker compose up -d

# Ver logs
docker compose logs -f
```

### Detener

```bash
docker compose down
```

---

## 🖥️ Despliegue en VPS (Nginx + Docker)

1. Sube el proyecto al VPS:
   ```bash
   scp -r . usuario@mi-vps:/opt/audiototext
   ```

2. En el VPS:
   ```bash
   cd /opt/audiototext
   cp .env.example .env
   # Edita .env con tu SECRET_KEY
   docker compose up -d
   ```

3. Configura Nginx como proxy inverso:
   ```nginx
   server {
       listen 80;
       server_name tu-dominio.com;

       client_max_body_size 500M;

       location / {
           proxy_pass http://127.0.0.1:5000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_read_timeout 600s;
       }
   }
   ```

4. SSL con Certbot:
   ```bash
   certbot --nginx -d tu-dominio.com
   ```

---

## ⚙️ Variables de entorno

| Variable     | Por defecto | Descripción                     |
|--------------|-------------|----------------------------------|
| `PORT`       | `5000`      | Puerto de la aplicación          |
| `SECRET_KEY` | (requerido) | Clave secreta Flask              |
| `FLASK_DEBUG`| `false`     | Modo debug (solo desarrollo)     |

---

## 📁 Estructura del proyecto

```
whisper_audio_linux/
├── app.py                  # Backend Flask
├── audiototext.py          # CLI original (Carleslc)
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .env.example
├── templates/
│   ├── index.html          # Página principal
│   └── history.html        # Historial
├── static/
│   ├── css/style.css
│   └── js/app.js
├── uploads/                # Archivos subidos (temporal)
└── audio_transcription/    # Resultados de transcripción
```

---

## 📝 Licencia

MIT — basado en [AudioToText](https://github.com/Carleslc/AudioToText) de Carleslc.
