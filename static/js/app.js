/* ──────────────────────────────────────────
   AudioToText Web — Frontend JS
   ────────────────────────────────────────── */

let selectedFile = null;
let currentJobId = null;
let pollInterval = null;

// ── Elementos DOM ──────────────────────────
const dropZone       = document.getElementById('dropZone');
const fileInput      = document.getElementById('fileInput');
const selectedFileEl = document.getElementById('selectedFile');
const selectedFileNameEl = document.getElementById('selectedFileName');
const removeFileBtn  = document.getElementById('removeFile');
const transcribeBtn  = document.getElementById('transcribeBtn');
const btnText        = document.getElementById('btnText');

const progressCard   = document.getElementById('progressCard');
const progressStatus = document.getElementById('progressStatus');
const progressPercent= document.getElementById('progressPercent');
const progressBar    = document.getElementById('progressBar');
const logBox         = document.getElementById('logBox');

const resultCard     = document.getElementById('resultCard');
const resultText     = document.getElementById('resultText');
const resultMeta     = document.getElementById('resultMeta');
const downloadButtons= document.getElementById('downloadButtons');
const copyBtn        = document.getElementById('copyBtn');
const newTransBtn    = document.getElementById('newTranscriptionBtn');

const errorCard      = document.getElementById('errorCard');
const errorMessage   = document.getElementById('errorMessage');
const retryBtn       = document.getElementById('retryBtn');

// ── Drag & Drop ────────────────────────────
dropZone.addEventListener('click', () => fileInput.click());

dropZone.addEventListener('dragover', e => {
  e.preventDefault();
  dropZone.classList.add('drag-over');
});

dropZone.addEventListener('dragleave', () => {
  dropZone.classList.remove('drag-over');
});

dropZone.addEventListener('drop', e => {
  e.preventDefault();
  dropZone.classList.remove('drag-over');
  const files = e.dataTransfer.files;
  if (files.length > 0) setFile(files[0]);
});

fileInput.addEventListener('change', () => {
  if (fileInput.files.length > 0) setFile(fileInput.files[0]);
});

removeFileBtn.addEventListener('click', () => clearFile());

function setFile(file) {
  selectedFile = file;
  selectedFileNameEl.textContent = file.name;
  selectedFileEl.classList.remove('hidden');
  transcribeBtn.disabled = false;
}

function clearFile() {
  selectedFile = null;
  fileInput.value = '';
  selectedFileEl.classList.add('hidden');
  transcribeBtn.disabled = true;
}

// ── Transcribir ────────────────────────────
transcribeBtn.addEventListener('click', startTranscription);

async function startTranscription() {
  if (!selectedFile) return;

  // Recoger opciones
  const model    = document.getElementById('modelSelect').value;
  const task     = document.getElementById('taskSelect').value;
  const language = document.getElementById('languageSelect').value;
  const prompt   = document.getElementById('promptInput').value;
  const formats  = [...document.querySelectorAll('input[name="output_formats"]:checked')]
                     .map(cb => cb.value);

  if (formats.length === 0) {
    alert('Selecciona al menos un formato de salida.');
    return;
  }

  // UI: mostrar progreso
  showSection('progress');
  setProgress(0, 'Subiendo archivo...');
  clearLog();

  const formData = new FormData();
  formData.append('audio', selectedFile);
  formData.append('model', model);
  formData.append('task', task);
  formData.append('language', language);
  formData.append('prompt', prompt);
  formData.append('output_formats', formats.join(','));

  try {
    btnText.textContent = '⏳ Procesando...';
    transcribeBtn.disabled = true;

    const res = await fetch('/upload', { method: 'POST', body: formData });
    const data = await res.json();

    if (!res.ok) {
      showError(data.error || 'Error al subir el archivo');
      return;
    }

    currentJobId = data.job_id;
    addLog(`Archivo recibido: ${data.filename}`);
    addLog(`Job ID: ${data.job_id}`);

    // Polling del estado
    pollInterval = setInterval(pollStatus, 1500);

  } catch (err) {
    showError('No se pudo conectar con el servidor: ' + err.message);
  }
}

async function pollStatus() {
  if (!currentJobId) return;

  try {
    const res = await fetch(`/status/${currentJobId}`);
    const job = await res.json();

    setProgress(job.progress, getStatusLabel(job.status));

    if (job.log && job.log.length > 0) {
      const lastLog = job.log[job.log.length - 1];
      if (logBox.lastEditorLine !== lastLog) {
        addLog(lastLog);
        logBox.lastEditorLine = lastLog;
      }
    }

    if (job.status === 'done') {
      clearInterval(pollInterval);
      showResult(job);
    } else if (job.status === 'error') {
      clearInterval(pollInterval);
      showError(job.error || 'Error desconocido durante la transcripción');
    }

  } catch (err) {
    console.error('Error polling:', err);
  }
}

function getStatusLabel(status) {
  const labels = {
    queued:  'En cola...',
    running: 'Transcribiendo...',
    done:    'Completado ✅',
    error:   'Error ❌'
  };
  return labels[status] || status;
}

// ── Resultado ──────────────────────────────
function showResult(job) {
  showSection('result');
  resultText.value = job.result_text;

  const lang = job.detected_language
    ? `Idioma detectado: <strong>${job.detected_language}</strong> · `
    : '';
  resultMeta.innerHTML = `${lang}Archivos guardados: ${job.files.length}`;

  downloadButtons.innerHTML = '';
  job.files.forEach(f => {
    const a = document.createElement('a');
    a.href = `/download/${currentJobId}/${f.filename}`;
    a.className = 'btn-download';
    a.textContent = `⬇ ${f.format.toUpperCase()}`;
    a.download = f.filename;
    downloadButtons.appendChild(a);
  });
}

// ── Copiar ─────────────────────────────────
copyBtn.addEventListener('click', () => {
  navigator.clipboard.writeText(resultText.value).then(() => {
    copyBtn.textContent = '✅ Copiado';
    setTimeout(() => { copyBtn.textContent = '📋 Copiar'; }, 2000);
  });
});

// ── Reset ──────────────────────────────────
newTransBtn.addEventListener('click', resetUI);
retryBtn.addEventListener('click', resetUI);

function resetUI() {
  clearInterval(pollInterval);
  currentJobId = null;
  clearFile();
  showSection('upload');
  clearLog();
  setProgress(0, 'Iniciando...');
  btnText.textContent = '🎙️ Transcribir';
}

// ── Helpers ────────────────────────────────
function showSection(section) {
  progressCard.classList.add('hidden');
  resultCard.classList.add('hidden');
  errorCard.classList.add('hidden');

  if (section === 'progress') progressCard.classList.remove('hidden');
  else if (section === 'result') resultCard.classList.remove('hidden');
  else if (section === 'error') errorCard.classList.remove('hidden');
}

function showError(msg) {
  showSection('error');
  errorMessage.textContent = msg;
  btnText.textContent = '🎙️ Transcribir';
  transcribeBtn.disabled = selectedFile === null;
}

function setProgress(percent, label) {
  progressBar.style.width = `${percent}%`;
  progressPercent.textContent = `${percent}%`;
  if (label) progressStatus.textContent = label;
}

function addLog(msg) {
  const span = document.createElement('span');
  span.className = 'log-line';
  span.textContent = `» ${msg}`;
  logBox.appendChild(span);
  logBox.scrollTop = logBox.scrollHeight;
}

function clearLog() {
  logBox.innerHTML = '';
  logBox.lastEditorLine = null;
}
