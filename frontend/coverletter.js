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

// Revision UI
const revisionInput  = document.getElementById('revision-input');
const revisionStatus = document.getElementById('revision-status');

const resultSummary  = document.getElementById('result-summary');
const letterContent  = document.getElementById('letter-content');

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
function showSection(section) {
    [setupSection, loadingSection, resultSection].forEach(el => el.hidden = true);
    section.hidden = false;
}

// ---------------------------------------------------------------------------
// 1. Generate Letter
// ---------------------------------------------------------------------------
btnGenerate.addEventListener('click', async () => {
    const cvFile = cvFileInput.files[0];
    const userCvText = cvInput.value.trim();
    const jobOffer = offerInput.value.trim();
    const exampleFiles = examplesInputs.files;
    const language = languageSelect.value;

    if (!cvFile && !userCvText) {
        alert('Veuillez importer votre CV ou en coller le texte avant de commencer.');
        return;
    }

    if (!jobOffer) {
        alert('Veuillez coller l\'offre d\'emploi ciblée.');
        return;
    }

    btnGenerate.disabled = true;
    showSection(loadingSection);

    const formData = new FormData();
    
    // Manage CV
    if (cvFile) {
        formData.append('cv_file', cvFile);
    } else {
        const textBlob = new Blob([userCvText], { type: 'text/plain' });
        formData.append('cv_file', textBlob, 'cv_paste.txt');
    }
    
    // Manage Offer
    formData.append('job_offer', jobOffer);

    // Manage Examples
    if (exampleFiles && exampleFiles.length > 0) {
        for (let i = 0; i < exampleFiles.length; i++) {
            formData.append('example_files', exampleFiles[i]);
        }
    }
    
    // Manage Language
    formData.append('language', language);

    try {
        const resp = await fetch('/api/cover-letter/generate', {
            method: 'POST',
            body: formData,
        });

        if (!resp.ok) {
            const err = await resp.json().catch(() => ({}));
            throw new Error(err.detail || `Erreur ${resp.status}`);
        }

        const data = await resp.json();
        
        // Render Result
        resultSummary.textContent = data.summary;
        letterContent.textContent = data.letter_body;
        
        showSection(resultSection);

    } catch (err) {
        alert(`Erreur lors de la génération : ${err.message}`);
        showSection(setupSection);
    } finally {
        btnGenerate.disabled = false;
        btnCopy.classList.remove('copied');
        btnCopy.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg> Copier';
    }
});

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
    } catch (err) {
        alert('Impossible de copier le texte automatiquement.');
    }
});

// ---------------------------------------------------------------------------
// 3. New Letter
// ---------------------------------------------------------------------------
btnNew.addEventListener('click', () => {
    cvFileInput.value = '';
    cvInput.value = '';
    offerInput.value = '';
    examplesInputs.value = '';
    revisionInput.value = '';
    resultSummary.textContent = '';
    letterContent.textContent = '';
    revisionStatus.classList.add('hidden');
    
    showSection(setupSection);
});

// ---------------------------------------------------------------------------
// 4. Revise Letter
// ---------------------------------------------------------------------------
btnRevise.addEventListener('click', async () => {
    const instructions = revisionInput.value.trim();
    if (!instructions) {
        alert('Veuillez spécifier la modification souhaitée.');
        return;
    }

    // Pass the raw text of the current letter
    const currentLetterText = letterContent.innerText;
    const language = languageSelect.value;
    
    // UI state loading
    btnRevise.disabled = true;
    revisionStatus.classList.remove('hidden');

    try {
        const resp = await fetch('/api/cover-letter/revise', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                current_letter: currentLetterText,
                instructions: instructions,
                language: language
            })
        });

        if (!resp.ok) {
            const err = await resp.json().catch(() => ({}));
            throw new Error(err.detail || `Erreur ${resp.status}`);
        }

        const data = await resp.json();
        
        // Output format mapping
        resultSummary.textContent = `[Révision] ${data.summary}`;
        letterContent.textContent = data.letter_body;
        
        // Clear input
        revisionInput.value = '';

    } catch (error) {
        console.error(error);
        alert(`Erreur lors de la révision : ${error.message}`);
    } finally {
        btnRevise.disabled = false;
        revisionStatus.classList.add('hidden');
    }
});
