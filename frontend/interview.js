/**
 * Coach Entretien — Frontend Logic
 *
 * Setup → Chat (multi-turn) → Feedback report
 * Conversation history is kept in-memory (stateless backend).
 */

// ---------------------------------------------------------------------------
// DOM
// ---------------------------------------------------------------------------
const setupSection   = document.getElementById('setup-section');
const chatSection    = document.getElementById('chat-section');
const loadingSection = document.getElementById('loading-section');
const feedbackSection= document.getElementById('feedback-section');
const statusText     = document.getElementById('status-text');

// Setup
const cvFileInput= document.getElementById('cv-file');
const cvInput    = document.getElementById('cv-input');
const offerInput = document.getElementById('offer-input');
const btnStart   = document.getElementById('btn-start');

// Chat
const chatMessages   = document.getElementById('chat-messages');
const userInput      = document.getElementById('user-input');
const btnSend        = document.getElementById('btn-send');
const btnVoiceRecord = document.getElementById('btn-voice-record');
const btnEnd         = document.getElementById('btn-end');

// Feedback
const scoreValue      = document.getElementById('score-value');
const feedbackSummary = document.getElementById('feedback-summary');
const strengthsList   = document.getElementById('strengths-list');
const improvementsList= document.getElementById('improvements-list');
const adviceText      = document.getElementById('advice-text');
const btnNewInterview = document.getElementById('btn-new-interview');

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------
let cvText  = '';
let jobOffer = '';
let messages = []; // { role, content }[]
let isSending = false;

// Voice recording state
let mediaRecorder = null;
let audioChunks   = [];

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
function showSection(section) {
    [setupSection, chatSection, loadingSection, feedbackSection].forEach(s => s.hidden = true);
    if (section) section.hidden = false;
}

function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str || '';
    return div.innerHTML;
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
    return bubble;
}

function removeTypingBubble() {
    const el = document.getElementById('typing-bubble');
    if (el) el.remove();
}

function setInputEnabled(enabled) {
    userInput.disabled = !enabled;
    btnSend.disabled = !enabled;
    btnVoiceRecord.disabled = !enabled;
    isSending = !enabled;
}

// ---------------------------------------------------------------------------
// 1. Start interview
// ---------------------------------------------------------------------------
btnStart.addEventListener('click', async () => {
    const cvFile = cvFileInput.files[0];
    const userCvText = cvInput.value.trim();
    jobOffer = offerInput.value.trim();

    if (!cvFile && !userCvText) {
        alert('Veuillez importer votre CV ou en coller le texte avant de commencer.');
        return;
    }

    if (!jobOffer) {
        alert('Veuillez coller l\'offre de stage/emploi avant de commencer.');
        return;
    }

    btnStart.disabled = true;
    btnStart.textContent = 'Démarrage…';

    const formData = new FormData();
    if (cvFile) {
        formData.append('cv_file', cvFile);
    } else {
        // Fallback: Si l'utilisateur a collé le texte, on crée un pseudo-fichier (Blob)
        // car le backend attend "cv_file: UploadFile"
        const textBlob = new Blob([userCvText], { type: 'text/plain' });
        formData.append('cv_file', textBlob, 'cv_paste.txt');
    }
    
    formData.append('job_offer', jobOffer);

    try {
        const resp = await fetch('/api/interview/start', {
            method: 'POST',
            body: formData,
        });

        if (!resp.ok) {
            const err = await resp.json().catch(() => ({}));
            throw new Error(err.detail || `Erreur ${resp.status}`);
        }

        const data = await resp.json();

        // Store the parsed CV context for subsequent chat turns
        cvText = data.extracted_cv_text;

        // Store the first assistant message
        messages = [{ role: 'assistant', content: data.first_question }];

        // Show chat
        showSection(chatSection);
        addBubble('assistant', data.first_question);
        userInput.focus();

    } catch (err) {
        alert('Erreur : ' + err.message);
        btnStart.disabled = false;
        btnStart.textContent = 'Démarrer l\'entretien';
    }
});

// ---------------------------------------------------------------------------
// 2. Send message
// ---------------------------------------------------------------------------
async function sendMessage() {
    const text = userInput.value.trim();
    if (!text || isSending) return;

    // Add user message
    messages.push({ role: 'user', content: text });
    addBubble('user', text);
    userInput.value = '';
    setInputEnabled(false);

    // Show typing indicator
    addTypingBubble();

    try {
        const resp = await fetch('/api/interview/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                cv_text: cvText,
                job_offer: jobOffer,
                messages: messages,
            }),
        });

        removeTypingBubble();

        if (!resp.ok) {
            const err = await resp.json().catch(() => ({}));
            throw new Error(err.detail || `Erreur ${resp.status}`);
        }

        const data = await resp.json();

        // Add assistant reply
        messages.push({ role: 'assistant', content: data.reply });
        addBubble('assistant', data.reply);

        // If the interview is done, trigger feedback
        if (data.is_final) {
            setTimeout(() => requestFeedback(), 1500);
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
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

// ---------------------------------------------------------------------------
// 2b. Record and send audio message
// ---------------------------------------------------------------------------
async function startRecording() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

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
            stream.getTracks().forEach(t => t.stop());
            const blob = new Blob(audioChunks, { type: mediaRecorder.mimeType || 'audio/webm' });
            sendAudioMessage(blob);
        };

        mediaRecorder.start();
        btnVoiceRecord.classList.add('recording');
        userInput.placeholder = "Enregistrement en cours…";
        setInputEnabled(false);
        // Re-enable just the voice button to stop
        isSending = true;
        btnVoiceRecord.disabled = false;
        
    } catch (err) {
        console.error('Microphone error:', err);
        alert("Impossible d'accéder au microphone.");
    }
}

function stopRecording() {
    if (mediaRecorder && mediaRecorder.state === 'recording') {
        mediaRecorder.stop();
        btnVoiceRecord.classList.remove('recording');
        userInput.placeholder = "Traitement audio…";
    }
}

async function sendAudioMessage(blob) {
    addTypingBubble();

    const formData = new FormData();
    const ext = blob.type.includes('webm') ? 'webm'
              : blob.type.includes('ogg')  ? 'ogg'
              : blob.type.includes('mp4')  ? 'm4a'
              : 'webm';
    formData.append('file', blob, `response.${ext}`);
    
    // Attach context as JSON string form field
    const contextObj = {
        cv_text: cvText,
        job_offer: jobOffer,
        messages: messages
    };
    formData.append('context', JSON.stringify(contextObj));

    try {
        const resp = await fetch('/api/interview/chat/audio', {
            method: 'POST',
            body: formData,
        });

        removeTypingBubble();

        if (!resp.ok) {
            const err = await resp.json().catch(() => ({}));
            throw new Error(err.detail || `Erreur ${resp.status}`);
        }

        const data = await resp.json();

        // 1. Show the user's transcribed text
        const transcriptText = data.user_transcript || "(Audio intercepté)";
        messages.push({ role: 'user', content: transcriptText });
        addBubble('user', transcriptText);

        // 2. Show the assistant's reply
        messages.push({ role: 'assistant', content: data.reply });
        addBubble('assistant', data.reply);

        if (data.is_final) {
            setTimeout(() => requestFeedback(), 1500);
            return;
        }

    } catch (err) {
        removeTypingBubble();
        addBubble('assistant', '⚠️ Erreur audio : ' + err.message);
    } finally {
        userInput.placeholder = "Tapez ou dictez votre réponse…";
        setInputEnabled(true);
        userInput.focus();
    }
}

btnVoiceRecord.addEventListener('click', () => {
    if (mediaRecorder && mediaRecorder.state === 'recording') {
        stopRecording();
    } else {
        startRecording();
    }
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

    try {
        const resp = await fetch('/api/interview/feedback', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                cv_text: cvText,
                job_offer: jobOffer,
                messages: messages,
            }),
        });

        if (!resp.ok) {
            const err = await resp.json().catch(() => ({}));
            throw new Error(err.detail || `Erreur ${resp.status}`);
        }

        const data = await resp.json();
        renderFeedback(data);

    } catch (err) {
        statusText.textContent = '⚠️ Erreur : ' + err.message;
    }
}

// ---------------------------------------------------------------------------
// 5. Render feedback
// ---------------------------------------------------------------------------
function renderFeedback(fb) {
    showSection(feedbackSection);

    scoreValue.textContent = fb.score;
    feedbackSummary.textContent = fb.summary;
    adviceText.textContent = fb.advice;

    // Strengths
    strengthsList.innerHTML = '';
    (fb.strengths || []).forEach(pt => {
        strengthsList.innerHTML += `
            <div class="feedback-point fort">
                <div class="fp-topic">${escapeHtml(pt.topic)}</div>
                <div class="fp-comment">${escapeHtml(pt.comment)}</div>
            </div>
        `;
    });

    // Improvements
    improvementsList.innerHTML = '';
    (fb.improvements || []).forEach(pt => {
        improvementsList.innerHTML += `
            <div class="feedback-point improve">
                <div class="fp-topic">${escapeHtml(pt.topic)}</div>
                <div class="fp-comment">${escapeHtml(pt.comment)}</div>
            </div>
        `;
    });
}

// ---------------------------------------------------------------------------
// 6. New interview
// ---------------------------------------------------------------------------
btnNewInterview.addEventListener('click', () => {
    messages = [];
    cvText = '';
    jobOffer = '';
    cvFileInput.value = '';
    cvInput.value = '';
    offerInput.value = '';
    chatMessages.innerHTML = '';
    btnStart.disabled = false;
    btnStart.innerHTML = 'Démarrer l\'entretien <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18"><path d="M5 12h14M12 5l7 7-7 7"/></svg>';
    setInputEnabled(true);
    showSection(setupSection);
});
