/**
 * Décodeur de Pensées — Frontend Logic
 *
 * MediaRecorder API → POST /api/process-audio → Render task cards
 */

// ---------------------------------------------------------------------------
// DOM Elements
// ---------------------------------------------------------------------------
const recordBtn     = document.getElementById('record-btn');
const recordLabel   = document.getElementById('record-label');
const micIcon       = document.getElementById('mic-icon');
const stopIcon      = document.getElementById('stop-icon');
const timerEl       = document.getElementById('timer');
const statusSection = document.getElementById('status-section');
const statusText    = document.getElementById('status-text');
const errorSection  = document.getElementById('error-section');
const errorText     = document.getElementById('error-text');
const btnRetry      = document.getElementById('btn-retry');
const resultsSection= document.getElementById('results-section');
const transcriptText= document.getElementById('transcript-text');
const tasksTitle    = document.getElementById('tasks-title');
const tasksGrid     = document.getElementById('tasks-grid');
const btnNew        = document.getElementById('btn-new');
const recorderSection = document.getElementById('recorder-section');

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------
let mediaRecorder = null;
let audioChunks   = [];
let timerInterval = null;
let seconds       = 0;

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
function formatTime(s) {
    const m = String(Math.floor(s / 60)).padStart(2, '0');
    const sec = String(s % 60).padStart(2, '0');
    return `${m}:${sec}`;
}

function showSection(section) {
    [statusSection, errorSection, resultsSection].forEach(s => s.hidden = true);
    if (section) section.hidden = false;
}

function resetUI() {
    showSection(null);
    recorderSection.hidden = false;
    recordBtn.classList.remove('recording');
    recordLabel.textContent = 'Cliquez pour enregistrer';
    timerEl.classList.remove('visible');
    timerEl.textContent = '00:00';
    seconds = 0;
}

// ---------------------------------------------------------------------------
// Timer
// ---------------------------------------------------------------------------
function startTimer() {
    seconds = 0;
    timerEl.textContent = '00:00';
    timerEl.classList.add('visible');
    timerInterval = setInterval(() => {
        seconds++;
        timerEl.textContent = formatTime(seconds);
    }, 1000);
}

function stopTimer() {
    clearInterval(timerInterval);
    timerInterval = null;
}

// ---------------------------------------------------------------------------
// Recording
// ---------------------------------------------------------------------------
async function startRecording() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

        // Pick a supported MIME type
        const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
            ? 'audio/webm;codecs=opus'
            : MediaRecorder.isTypeSupported('audio/webm')
                ? 'audio/webm'
                : '';

        mediaRecorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
        audioChunks = [];

        mediaRecorder.ondataavailable = (e) => {
            if (e.data.size > 0) audioChunks.push(e.data);
        };

        mediaRecorder.onstop = () => {
            // Stop all tracks to release the microphone
            stream.getTracks().forEach(t => t.stop());
            stopTimer();

            const blob = new Blob(audioChunks, { type: mediaRecorder.mimeType || 'audio/webm' });
            sendAudio(blob);
        };

        mediaRecorder.start();
        recordBtn.classList.add('recording');
        recordLabel.textContent = 'Enregistrement… Cliquez pour arrêter';
        startTimer();
    } catch (err) {
        console.error('Microphone error:', err);
        showError("Impossible d'accéder au microphone. Vérifiez les permissions de votre navigateur.");
    }
}

function stopRecording() {
    if (mediaRecorder && mediaRecorder.state === 'recording') {
        mediaRecorder.stop();
        recordBtn.classList.remove('recording');
        recordLabel.textContent = 'Traitement en cours…';
        timerEl.classList.remove('visible');
    }
}

// ---------------------------------------------------------------------------
// Send audio to backend
// ---------------------------------------------------------------------------
async function sendAudio(blob) {
    recorderSection.hidden = true;
    showSection(statusSection);
    statusText.textContent = '🎙️ Envoi de l\'audio…';

    const formData = new FormData();
    // Determine extension from MIME
    const ext = blob.type.includes('webm') ? 'webm'
              : blob.type.includes('ogg')  ? 'ogg'
              : blob.type.includes('mp4')  ? 'm4a'
              : 'webm';
    formData.append('file', blob, `braindump.${ext}`);

    try {
        statusText.textContent = '🔄 Transcription et analyse en cours…';

        const response = await fetch('/api/process-audio', {
            method: 'POST',
            body: formData,
        });

        if (!response.ok) {
            const errData = await response.json().catch(() => ({}));
            throw new Error(errData.detail || `Erreur serveur (${response.status})`);
        }

        const data = await response.json();
        renderResults(data);
    } catch (err) {
        console.error('API error:', err);
        showError(err.message || 'Une erreur est survenue lors du traitement.');
    }
}

// ---------------------------------------------------------------------------
// Render results
// ---------------------------------------------------------------------------
function renderResults(data) {
    showSection(resultsSection);

    // Transcript
    transcriptText.textContent = data.transcript || '(aucune transcription)';

    // Tasks
    tasksGrid.innerHTML = '';
    const tasks = data.tasks || [];
    tasksTitle.textContent = tasks.length > 0
        ? `✅ ${tasks.length} tâche${tasks.length > 1 ? 's' : ''} extraite${tasks.length > 1 ? 's' : ''}`
        : '🤷 Aucune tâche identifiée';

    tasks.forEach((task, i) => {
        const card = document.createElement('div');
        card.className = 'task-card';
        card.style.animationDelay = `${i * 0.08}s`;

        const priorityClass = (task.priority || 'moyenne').toLowerCase();

        card.innerHTML = `
            <div class="task-card-header">
                <span class="task-title">${escapeHtml(task.title)}</span>
                <span class="task-priority ${priorityClass}">${escapeHtml(task.priority)}</span>
            </div>
            <p class="task-description">${escapeHtml(task.description)}</p>
        `;

        tasksGrid.appendChild(card);
    });
}

function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str || '';
    return div.innerHTML;
}

// ---------------------------------------------------------------------------
// Error display
// ---------------------------------------------------------------------------
function showError(message) {
    showSection(errorSection);
    errorText.textContent = message;
}

// ---------------------------------------------------------------------------
// Event Listeners
// ---------------------------------------------------------------------------
recordBtn.addEventListener('click', () => {
    if (mediaRecorder && mediaRecorder.state === 'recording') {
        stopRecording();
    } else {
        startRecording();
    }
});

btnRetry.addEventListener('click', resetUI);
btnNew.addEventListener('click', resetUI);
