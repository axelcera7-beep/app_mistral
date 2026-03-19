/**
 * coverletter.js — Generate and revise cover letters.
 * Relies on auth.js (apiRequest, withAuth, escapeHtml, debounce).
 */

// ---------------------------------------------------------------------------
// DOM Elements
// ---------------------------------------------------------------------------
const setupSection   = document.getElementById('setup-section');
const loadingSection = document.getElementById('loading-section');
const resultSection  = document.getElementById('result-section');

const cvFileInput    = document.getElementById('cv-file');
const cvInput        = document.getElementById('cv-input');
const offerInput     = document.getElementById('offer-input');
const examplesInputs = document.getElementById('examples-files');
const languageSelect = document.getElementById('language-select');

const btnGenerate    = document.getElementById('btn-generate');
const btnNew         = document.getElementById('btn-new');
const btnCopy        = document.getElementById('btn-copy');
const btnRevise      = document.getElementById('btn-revise');

const revisionInput  = document.getElementById('revision-input');
const revisionStatus = document.getElementById('revision-status');
const generateError  = document.getElementById('generate-error');

const letterContent  = document.getElementById('letter-content');

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
function showSection(section) {
    [setupSection, loadingSection, resultSection].forEach(el => el.hidden = true);
    section.hidden = false;
}

function showGenerateError(msg) {
    if (!generateError) { console.error(msg); return; }
    generateError.textContent = msg;
    generateError.hidden = false;
}

function hideGenerateError() {
    if (generateError) generateError.hidden = true;
}

// ---------------------------------------------------------------------------
// 1. Generate Letter (debounced to prevent double-submission)
// ---------------------------------------------------------------------------
async function doGenerate() {
    const cvFile      = cvFileInput.files[0];
    const userCvText  = cvInput.value.trim();
    const jobOffer    = offerInput.value.trim();
    const exampleFiles = examplesInputs.files;
    const language    = languageSelect.value;

    hideGenerateError();

    if (!cvFile && !userCvText) {
        showGenerateError('Veuillez importer votre CV ou en coller le texte avant de commencer.');
        return;
    }
    if (!jobOffer) {
        showGenerateError("Veuillez coller l'offre d'emploi ciblée.");
        return;
    }

    btnGenerate.disabled = true;
    showSection(loadingSection);

    const formData = new FormData();

    if (cvFile) {
        formData.append('cv_file', cvFile);
    } else {
        formData.append('cv_file', new Blob([userCvText], { type: 'text/plain' }), 'cv_paste.txt');
    }

    formData.append('job_offer', jobOffer);
    formData.append('language', language);

    for (const file of exampleFiles) {
        formData.append('example_files', file);
    }

    try {
        const data = await apiRequest('/api/cover-letter/generate', withAuth({ method: 'POST', body: formData }));

        letterContent.textContent = data.letter_body;
        showSection(resultSection);

        const matchScoreBox = document.getElementById('match-score-box');
        if (matchScoreBox) matchScoreBox.style.display = 'none';

    } catch (err) {
        showGenerateError(`Erreur lors de la génération : ${err.message}`);
        showSection(setupSection);
    } finally {
        btnGenerate.disabled = false;
        btnCopy.classList.remove('copied');
        btnCopy.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg> Copier';
    }
}

btnGenerate.addEventListener('click', debounce(doGenerate, 400));

// ---------------------------------------------------------------------------
// 2. Copy to Clipboard
// ---------------------------------------------------------------------------
btnCopy.addEventListener('click', async () => {
    try {
        await navigator.clipboard.writeText(letterContent.textContent);
        btnCopy.classList.add('copied');
        btnCopy.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18"><polyline points="20 6 9 17 4 12"></polyline></svg> Copié !';
        setTimeout(() => {
            btnCopy.classList.remove('copied');
            btnCopy.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg> Copier';
        }, 2000);
    } catch {
        alert('Impossible de copier le texte automatiquement.');
    }
});

// ---------------------------------------------------------------------------
// 3. New Letter
// ---------------------------------------------------------------------------
btnNew.addEventListener('click', () => {
    cvFileInput.value    = '';
    cvInput.value        = '';
    offerInput.value     = '';
    examplesInputs.value = '';
    revisionInput.value  = '';
    letterContent.textContent = '';
    hideGenerateError();
    if (revisionStatus) revisionStatus.classList.add('hidden');
    showSection(setupSection);
});

// ---------------------------------------------------------------------------
// 4. Revise Letter (debounced to prevent double-submission)
// ---------------------------------------------------------------------------
async function doRevise() {
    const instructions = revisionInput.value.trim();
    if (!instructions) {
        alert('Veuillez spécifier la modification souhaitée.');
        return;
    }

    btnRevise.disabled = true;
    if (revisionStatus) revisionStatus.classList.remove('hidden');

    try {
        const data = await apiRequest('/api/cover-letter/revise', withAuth({
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                current_letter: letterContent.innerText,
                instructions,
                language: languageSelect.value,
                job_offer: offerInput.value.trim(),
            }),
        }));

        letterContent.textContent = data.letter_body;
        revisionInput.value = '';

    } catch (err) {
        alert(`Erreur lors de la révision : ${err.message}`);
    } finally {
        btnRevise.disabled = false;
        if (revisionStatus) revisionStatus.classList.add('hidden');
    }
}

btnRevise.addEventListener('click', debounce(doRevise, 400));

// ---------------------------------------------------------------------------
// Pre-fill job offer from Job Search page (via localStorage relay)
// ---------------------------------------------------------------------------
document.addEventListener('DOMContentLoaded', () => {
    const prefilledJob = localStorage.getItem('last_job_offer');
    if (prefilledJob && offerInput) {
        offerInput.value = prefilledJob;
        localStorage.removeItem('last_job_offer');
    }
});
