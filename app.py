# -*- coding: utf-8 -*-
"""
AudioToText Web App
Flask web interface for Whisper audio transcription
"""

import os
import uuid
import json
import threading
import time
from pathlib import Path

from flask import (
    Flask, render_template, request, jsonify,
    send_from_directory, Response, stream_with_context
)
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'whisper-secret-key-2024')
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['OUTPUT_FOLDER'] = 'audio_transcription'
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500 MB

# Extensiones de audio/video soportadas
ALLOWED_EXTENSIONS = {
    'mp3', 'mp4', 'wav', 'ogg', 'm4a', 'flac', 'aac',
    'wma', 'opus', 'webm', 'mkv', 'avi', 'mov', 'mpeg',
    'mpg', '3gp', 'amr', 'aiff', 'aif'
}

# Estado de los trabajos en memoria
jobs = {}

WHISPER_MODELS = ['tiny', 'base']

LANGUAGES = [
    'Auto-Detect', 'Afrikaans', 'Albanian', 'Amharic', 'Arabic', 'Armenian',
    'Azerbaijani', 'Basque', 'Belarusian', 'Bengali', 'Bosnian', 'Breton',
    'Bulgarian', 'Burmese', 'Catalan', 'Chinese', 'Croatian', 'Czech',
    'Danish', 'Dutch', 'English', 'Estonian', 'Finnish', 'French',
    'Galician', 'Georgian', 'German', 'Greek', 'Gujarati', 'Hausa',
    'Hawaiian', 'Hebrew', 'Hindi', 'Hungarian', 'Icelandic', 'Indonesian',
    'Italian', 'Japanese', 'Javanese', 'Kannada', 'Kazakh', 'Khmer',
    'Korean', 'Lao', 'Latin', 'Latvian', 'Lithuanian', 'Macedonian',
    'Malagasy', 'Malay', 'Malayalam', 'Maltese', 'Maori', 'Marathi',
    'Mongolian', 'Nepali', 'Norwegian', 'Persian', 'Polish', 'Portuguese',
    'Punjabi', 'Romanian', 'Russian', 'Sanskrit', 'Serbian', 'Sinhala',
    'Slovak', 'Slovenian', 'Somali', 'Spanish', 'Swahili', 'Swedish',
    'Tagalog', 'Tajik', 'Tamil', 'Telugu', 'Thai', 'Turkish', 'Ukrainian',
    'Urdu', 'Uzbek', 'Vietnamese', 'Welsh', 'Yiddish', 'Yoruba'
]

OUTPUT_FORMATS = ['txt', 'vtt', 'srt', 'tsv', 'json']


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def run_transcription(job_id, file_path, options):
    """Ejecuta la transcripción en un hilo separado."""
    job = jobs[job_id]
    job['status'] = 'running'
    job['progress'] = 5
    job['log'] = []

    try:
        import whisper
        import numpy as np

        # Cargar modelo
        model_name = options.get('model', 'small')
        job['log'].append(f'Cargando modelo Whisper: {model_name}...')
        job['progress'] = 10

        model = whisper.load_model(model_name)
        job['log'].append(f'Modelo {model_name} cargado.')
        job['progress'] = 30

        # Configurar opciones
        language = options.get('language', 'Auto-Detect')
        task = options.get('task', 'transcribe')
        output_formats = options.get('output_formats', ['txt', 'vtt', 'srt'])
        prompt = options.get('prompt', '')

        transcribe_kwargs = {
            'task': task,
            'verbose': False,
        }

        if language and language != 'Auto-Detect':
            transcribe_kwargs['language'] = language

        if prompt:
            transcribe_kwargs['initial_prompt'] = prompt

        job['log'].append(f'Transcribiendo archivo... (tarea: {task})')
        job['progress'] = 40

        # Transcribir
        result = model.transcribe(file_path, **transcribe_kwargs)

        job['log'].append('Transcripción completada.')
        job['progress'] = 80

        # Guardar resultados
        output_dir = os.path.join(app.config['OUTPUT_FOLDER'], job_id)
        os.makedirs(output_dir, exist_ok=True)

        base_name = Path(file_path).stem
        saved_files = []

        if 'txt' in output_formats:
            txt_path = os.path.join(output_dir, f'{base_name}.txt')
            with open(txt_path, 'w', encoding='utf-8') as f:
                f.write(result['text'].strip())
            saved_files.append({'format': 'txt', 'filename': f'{base_name}.txt'})

        if 'json' in output_formats:
            json_path = os.path.join(output_dir, f'{base_name}.json')
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            saved_files.append({'format': 'json', 'filename': f'{base_name}.json'})

        if 'vtt' in output_formats:
            vtt_path = os.path.join(output_dir, f'{base_name}.vtt')
            with open(vtt_path, 'w', encoding='utf-8') as f:
                f.write('WEBVTT\n\n')
                for i, segment in enumerate(result['segments']):
                    start = format_timestamp_vtt(segment['start'])
                    end = format_timestamp_vtt(segment['end'])
                    f.write(f'{start} --> {end}\n{segment["text"].strip()}\n\n')
            saved_files.append({'format': 'vtt', 'filename': f'{base_name}.vtt'})

        if 'srt' in output_formats:
            srt_path = os.path.join(output_dir, f'{base_name}.srt')
            with open(srt_path, 'w', encoding='utf-8') as f:
                for i, segment in enumerate(result['segments'], 1):
                    start = format_timestamp_srt(segment['start'])
                    end = format_timestamp_srt(segment['end'])
                    f.write(f'{i}\n{start} --> {end}\n{segment["text"].strip()}\n\n')
            saved_files.append({'format': 'srt', 'filename': f'{base_name}.srt'})

        if 'tsv' in output_formats:
            tsv_path = os.path.join(output_dir, f'{base_name}.tsv')
            with open(tsv_path, 'w', encoding='utf-8') as f:
                f.write('start\tend\ttext\n')
                for segment in result['segments']:
                    start_ms = int(segment['start'] * 1000)
                    end_ms = int(segment['end'] * 1000)
                    f.write(f'{start_ms}\t{end_ms}\t{segment["text"].strip()}\n')
            saved_files.append({'format': 'tsv', 'filename': f'{base_name}.tsv'})

        job['progress'] = 100
        job['status'] = 'done'
        job['result_text'] = result['text'].strip()
        job['detected_language'] = result.get('language', 'unknown')
        job['files'] = saved_files
        job['output_dir'] = job_id
        job['log'].append(f'Archivos guardados: {[f["filename"] for f in saved_files]}')

    except Exception as e:
        job['status'] = 'error'
        job['error'] = str(e)
        job['log'].append(f'Error: {str(e)}')


def format_timestamp_vtt(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f'{h:02d}:{m:02d}:{s:06.3f}'


def format_timestamp_srt(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f'{h:02d}:{m:02d}:{s:02d},{ms:03d}'


# ─── RUTAS ────────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return render_template('index.html',
                           models=WHISPER_MODELS,
                           languages=LANGUAGES,
                           output_formats=OUTPUT_FORMATS)


@app.route('/upload', methods=['POST'])
def upload_file():
    if 'audio' not in request.files:
        return jsonify({'error': 'No se recibió ningún archivo'}), 400

    file = request.files['audio']
    if file.filename == '':
        return jsonify({'error': 'Nombre de archivo vacío'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': 'Formato de archivo no soportado'}), 400

    # Generar job ID único
    job_id = str(uuid.uuid4())
    filename = secure_filename(file.filename)
    upload_path = os.path.join(app.config['UPLOAD_FOLDER'], job_id)
    os.makedirs(upload_path, exist_ok=True)

    file_path = os.path.join(upload_path, filename)
    file.save(file_path)

    # Opciones de transcripción
    options = {
        'model': request.form.get('model', 'tiny'),
        'language': request.form.get('language', 'Auto-Detect'),
        'task': request.form.get('task', 'transcribe'),
        'output_formats': request.form.get('output_formats', 'txt,vtt,srt').split(','),
        'prompt': request.form.get('prompt', ''),
    }

    # Crear job
    jobs[job_id] = {
        'id': job_id,
        'filename': filename,
        'status': 'queued',
        'progress': 0,
        'log': [],
        'result_text': '',
        'files': [],
        'error': '',
        'created_at': time.time()
    }

    # Lanzar transcripción en hilo
    thread = threading.Thread(
        target=run_transcription,
        args=(job_id, file_path, options),
        daemon=True
    )
    thread.start()

    return jsonify({'job_id': job_id, 'filename': filename})


@app.route('/status/<job_id>')
def job_status(job_id):
    job = jobs.get(job_id)
    if not job:
        return jsonify({'error': 'Job no encontrado'}), 404
    return jsonify(job)


@app.route('/download/<job_id>/<filename>')
def download_file(job_id, filename):
    output_dir = os.path.join(app.config['OUTPUT_FOLDER'], job_id)
    return send_from_directory(output_dir, filename, as_attachment=True)


@app.route('/history')
def history():
    job_list = sorted(
        [j for j in jobs.values()],
        key=lambda x: x.get('created_at', 0),
        reverse=True
    )
    return render_template('history.html', jobs=job_list)


@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'version': '1.0.0'})


if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    app.run(host='0.0.0.0', port=port, debug=debug)
