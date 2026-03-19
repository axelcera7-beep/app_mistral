/**
 * interview.js — Coach Entretien
 * Setup → Chat (multi-turn) → Feedback report
 * Conversation history is kept in-memory (stateless backend).
 * Relies on auth.js (apiRequest, withAuth, escapeHtml).
 */

// ---------------------------------------------------------------------------
// DOM
// ---------------------------------------------------------------------------
const setupSection    = document.getElementById('setup-section');
const chatSection     = document.getElementById('chat-section');
const loadingSection  = document.getElementById('loading-section');
const feedbackSection = document.getElementById('feedback-section');
const statusText      = document.getElementById('status-text');

// Setup
const cvFileInput  = document.getElementById('cv-file');
const cvInput      = document.getElementById('cv-input');
const offerInput   = document.getElementById('offer-input');
const btnStart     = document.getElementById('btn-start');

// Chat
const chatMessages  = document.getElementById('chat-messages');
const userInput     = document.getElementById('user-input');
const btnSend       = document.getElementById('btn-send');
const btnVoiceRecord = document.getElementById('btn-voice-record');
const btnEnd        = document.getElementById('btn-end');

// Feedback
const scoreValue       = document.getElementById('score-value');
const feedbackSummary  = document.getElementById('feedback-summary');
const strengthsList    = document.getElementById('strengths-list');
const improvementsList = document.getElementById('improvements-list');
const adviceText       = document.getElementById('advice-text');
const btnNewInterview  = document.getElementById('btn-new-interview');

// Webcam
const webcamToggle = document.getElementById('webcam-toggle');
const webcamPip    = document.getElementById('webcam-pip');
const webcamVideo  = document.getElementById('webcam-video');

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------
let cvText   = '';
let jobOffer = '';
let messages = []; // { role, content }[]
let isSending = false;

let mediaRecorder  = null;
let audioChunks    = [];
let webcamStream   = null;
let capturedFrames = [];
let captureInterval = null;

const CAPTURE_INTERVAL_MS = 10_000; // capture every 10s for finer temporal resolution

// ---------------------------------------------------------------------------
// UI helpers
// ---------------------------------------------------------------------------
function showSection(section) {
    [setupSection, chatSection, loadingSection, feedbackSection].forEach(s => s.hidden = true);
    if (section) section.hidden = false;
}

function addBubble(role, content) {
    const bubble = document.createElement('div');
    bubble.className = `bubble ${role}`;
    bubble.innerHTML = escapeHtml(content).replace(/\n/g, '<br>');
    chatMessages.appendChild(bubble);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    return bubble;
}

function addTypingBubble() {
    const bubble = document.createElement('div');
    bubble.className = 'bubble typing';
    bubble.id = 'typing-bubble';
    bubble.innerHTML = 'Le recruteur réfléchit<span class="typing-dots"></span>';
    chatMessages.appendChild(bubble);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function removeTypingBubble() {
    document.getElementById('typing-bubble')?.remove();
}

function setInputEnabled(enabled) {
    userInput.disabled    = !enabled;
    btnSend.disabled      = !enabled;
    btnVoiceRecord.disabled = !enabled;
    isSending = !enabled;
}

// ---------------------------------------------------------------------------
// 1. Start interview
// ---------------------------------------------------------------------------
btnStart.addEventListener('click', async () => {
    const cvFile     = cvFileInput.files[0];
    const userCvText = cvInput.value.trim();
    jobOffer         = offerInput.value.trim();

    if (!cvFile && !userCvText) {
        alert('Veuillez importer votre CV ou en coller le texte avant de commencer.');
        return;
    }
    if (!jobOffer) {
        alert("Veuillez coller l'offre de stage/emploi avant de commencer.");
        return;
    }

    btnStart.disabled   = true;
    btnStart.textContent = 'Démarrage…';

    const formData = new FormData();
    if (cvFile) {
        formData.append('cv_file', cvFile);
    } else {
        formData.append('cv_file', new Blob([userCvText], { type: 'text/plain' }), 'cv_paste.txt');
    }
    formData.append('job_offer', jobOffer);

    try {
        const data = await apiRequest('/api/interview/start', { method: 'POST', body: formData });

        cvText = data.extracted_cv_text;
        messages = [{ role: 'assistant', content: data.first_question }];

        if (webcamToggle.checked) await startWebcam();

        showSection(chatSection);
        addBubble('assistant', data.first_question);
        setInputEnabled(true);
        userInput.focus();

    } catch (err) {
        alert('Erreur : ' + err.message);
        btnStart.disabled   = false;
        btnStart.textContent = "Démarrer l'entretien";
    }
});

// ---------------------------------------------------------------------------
// 2. Send text message
// ---------------------------------------------------------------------------
async function sendMessage() {
    const text = userInput.value.trim();
    if (!text || isSending) return;

    messages.push({ role: 'user', content: text });
    addBubble('user', text);
    userInput.value = '';
    setInputEnabled(false);
    addTypingBubble();

    try {
        const data = await apiRequest('/api/interview/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ cv_text: cvText, job_offer: jobOffer, messages }),
        });

        removeTypingBubble();
        messages.push({ role: 'assistant', content: data.reply });
        addBubble('assistant', data.reply);

        btnEnd.disabled = false;

        if (data.is_final) {
            setTimeout(requestFeedback, 1500);
            return;
        }

        setInputEnabled(true);
        userInput.focus();

    } catch (err) {
        removeTypingBubble();
        addBubble('assistant', '⚠️ Erreur : ' + err.message);
        setInputEnabled(true);
    }
}

btnSend.addEventListener('click', sendMessage);
userInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
});

// ---------------------------------------------------------------------------
// 2b. Voice recording
// ---------------------------------------------------------------------------
async function startRecording() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

        const mimeType = ['audio/webm;codecs=opus', 'audio/webm'].find(t => MediaRecorder.isTypeSupported(t)) ?? '';
        mediaRecorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
        audioChunks   = [];

        mediaRecorder.ondataavailable = (e) => { if (e.data.size > 0) audioChunks.push(e.data); };
        mediaRecorder.onstop = () => {
            stream.getTracks().forEach(t => t.stop());
            sendAudioMessage(new Blob(audioChunks, { type: mediaRecorder.mimeType || 'audio/webm' }));
        };

        mediaRecorder.start();
        btnVoiceRecord.classList.add('recording');
        userInput.placeholder = 'Enregistrement en cours…';
        isSending = true;
        btnVoiceRecord.disabled = false;

    } catch (err) {
        console.warn('Microphone error:', err);
        alert("Impossible d'accéder au microphone.");
    }
}

function stopRecording() {
    if (mediaRecorder?.state === 'recording') {
        mediaRecorder.stop();
        btnVoiceRecord.classList.remove('recording');
        userInput.placeholder = 'Traitement audio…';
    }
}

async function sendAudioMessage(blob) {
    addTypingBubble();

    const ext = blob.type.includes('ogg') ? 'ogg' : blob.type.includes('mp4') ? 'm4a' : 'webm';
    const formData = new FormData();
    formData.append('file', blob, `response.${ext}`);
    formData.append('context', JSON.stringify({ cv_text: cvText, job_offer: jobOffer, messages }));

    try {
        const data = await apiRequest('/api/interview/chat/audio', { method: 'POST', body: formData });

        removeTypingBubble();

        const transcript = data.user_transcript || '(Audio intercepté)';
        messages.push({ role: 'user', content: transcript });
        addBubble('user', transcript);

        messages.push({ role: 'assistant', content: data.reply });
        addBubble('assistant', data.reply);

        btnEnd.disabled = false;

        if (data.is_final) {
            setTimeout(requestFeedback, 1500);
            return;
        }

    } catch (err) {
        removeTypingBubble();
        addBubble('assistant', '⚠️ Erreur audio : ' + err.message);
    } finally {
        userInput.placeholder = 'Tapez ou dictez votre réponse…';
        setInputEnabled(true);
        userInput.focus();
    }
}

btnVoiceRecord.addEventListener('click', () => {
    mediaRecorder?.state === 'recording' ? stopRecording() : startRecording();
});

// ---------------------------------------------------------------------------
// 3. End interview manually
// ---------------------------------------------------------------------------
btnEnd.addEventListener('click', () => {
    if (messages.length < 3) {
        alert('Répondez à au moins quelques questions avant de terminer.');
        return;
    }
    requestFeedback();
});

// ---------------------------------------------------------------------------
// 4. Request feedback
// ---------------------------------------------------------------------------
async function requestFeedback() {
    showSection(loadingSection);
    statusText.textContent = '📊 Génération du compte rendu…';

    let visualReport = null;
    let visualError  = null;

    if (capturedFrames.length > 0) {
        const framesToSend = sampleFrames(capturedFrames);
        statusText.textContent = `📹 Analyse visuelle (${framesToSend.length} cadres sur ${capturedFrames.length})…`;
        try {
            const vaResp = await fetch('/api/interview/visual-analysis', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ frames: framesToSend, job_offer: jobOffer }),
            });
            if (vaResp.ok) {
                visualReport = await vaResp.json();
            } else {
                visualError = `Erreur serveur (${vaResp.status})`;
            }
        } catch (err) {
            visualError = err.message;
        }
        statusText.textContent = '📊 Génération du compte rendu…';
    } else {
        visualError = webcamToggle.checked
            ? "Aucune image capturée (la webcam n'a peut-être pas démarré)"
            : 'Webcam désactivée';
    }

    stopWebcam();

    try {
        const data = await apiRequest('/api/interview/feedback', withAuth({
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                cv_text: cvText, job_offer: jobOffer,
                messages, visual_report: visualReport,
            }),
        }));

        renderFeedback(data, visualReport ?? data.visual_report ?? null, visualError);

    } catch (err) {
        statusText.textContent = '⚠️ Erreur : ' + err.message;
    }
}

// ---------------------------------------------------------------------------
// 5. Render feedback
// ---------------------------------------------------------------------------
function renderFeedback(fb, visualReport, visualError) {
    showSection(feedbackSection);

    scoreValue.textContent    = fb.score;
    feedbackSummary.textContent = fb.summary;
    adviceText.textContent    = fb.advice;

    strengthsList.innerHTML = (fb.strengths || []).map(pt => `
        <div class="feedback-point fort">
            <div class="fp-topic">${escapeHtml(pt.topic)}</div>
            <div class="fp-comment">${escapeHtml(pt.comment)}</div>
        </div>
    `).join('');

    improvementsList.innerHTML = (fb.improvements || []).map(pt => `
        <div class="feedback-point improve">
            <div class="fp-topic">${escapeHtml(pt.topic)}</div>
            <div class="fp-comment">${escapeHtml(pt.comment)}</div>
        </div>
    `).join('');

    renderVisualReport(visualReport, visualError);
}

// ---------------------------------------------------------------------------
// 6. New interview
// ---------------------------------------------------------------------------
btnNewInterview.addEventListener('click', () => {
    messages = [];
    cvText   = '';
    jobOffer = '';
    cvFileInput.value = '';
    cvInput.value     = '';
    offerInput.value  = '';
    chatMessages.innerHTML = '';
    capturedFrames = [];
    stopWebcam();
    btnStart.disabled = false;
    btnStart.innerHTML = 'Démarrer l\'entretien <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18"><path d="M5 12h14M12 5l7 7-7 7"/></svg>';
    setInputEnabled(true);
    showSection(setupSection);
});

// ---------------------------------------------------------------------------
// Webcam management
// ---------------------------------------------------------------------------
async function startWebcam() {
    try {
        webcamStream = await navigator.mediaDevices.getUserMedia({ video: true });
        webcamVideo.srcObject = webcamStream;
        webcamPip.hidden = false;
        capturedFrames = [];
        setTimeout(captureFrame, 2000);
        captureInterval = setInterval(captureFrame, CAPTURE_INTERVAL_MS);
    } catch (err) {
        console.warn('Could not access webcam:', err);
        webcamPip.hidden = true;
    }
}

function stopWebcam() {
    clearInterval(captureInterval);
    captureInterval = null;
    webcamStream?.getTracks().forEach(t => t.stop());
    webcamStream = null;
    webcamVideo.srcObject = null;
    webcamPip.hidden = true;
}

// Select up to maxCount evenly-spaced frames from the full captured array.
// Ensures the visual analysis covers the whole interview, not just the end.
function sampleFrames(frames, maxCount = 5) {
    if (frames.length <= maxCount) return frames;
    const step = frames.length / maxCount;
    return Array.from({ length: maxCount }, (_, i) => frames[Math.floor(i * step)]);
}

function captureFrame() {
    if (!webcamVideo?.videoWidth) return;

    const canvas = document.createElement('canvas');
    const w = Math.min(webcamVideo.videoWidth, 960);  // higher res for better facial analysis
    const h = Math.round(w * (webcamVideo.videoHeight / webcamVideo.videoWidth));
    canvas.width  = w;
    canvas.height = h;

    canvas.getContext('2d').drawImage(webcamVideo, 0, 0, w, h);
    capturedFrames.push(canvas.toDataURL('image/jpeg', 0.85).split(',')[1]); // higher quality
}

// ---------------------------------------------------------------------------
// Visual report rendering
// ---------------------------------------------------------------------------
function renderVisualReport(report, error) {
    const card = document.getElementById('visual-report-card');
    if (!report) {
        if (error) {
            card.hidden = false;
            card.innerHTML = `
                <h2>📹 Analyse Visuelle</h2>
                <p class="visual-impression" style="color: var(--text-muted, #888);">
                    Analyse visuelle indisponible : ${escapeHtml(error)}
                </p>`;
        } else {
            card.hidden = true;
        }
        return;
    }

    card.hidden = false;
    document.getElementById('visual-score-value').textContent = report.confidence_score;
    document.getElementById('visual-impression').textContent  = report.overall_impression;

    document.getElementById('visual-observations').innerHTML = (report.observations || []).map(obs => {
        const badgeClass = obs.assessment === 'positif' ? 'badge-positif'
            : obs.assessment === 'neutre' ? 'badge-neutre'
            : 'badge-ameliorer';
        return `
            <div class="visual-obs-item">
                <span class="visual-obs-badge ${badgeClass}">${escapeHtml(obs.category)}</span>
                <span class="visual-obs-text">${escapeHtml(obs.observation)}</span>
            </div>`;
    }).join('');

    document.getElementById('visual-recommendations-list').innerHTML =
        (report.recommendations || []).map(rec => `<li>${escapeHtml(rec)}</li>`).join('');
}
