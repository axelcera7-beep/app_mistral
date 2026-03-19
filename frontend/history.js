/**
 * history.js — Saved cover letters, interview reports, and job offers.
 * Relies on auth.js (apiRequest, escapeHtml, formatDate, b64Encode, b64Decode, isLoggedIn).
 */

// ---------------------------------------------------------------------------
// DOM
// ---------------------------------------------------------------------------
const authRequired   = document.getElementById('auth-required');
const historyContent = document.getElementById('history-content');

const tabLetters    = document.getElementById('tab-letters');
const tabInterviews = document.getElementById('tab-interviews');
const tabJobs       = document.getElementById('tab-jobs');

const panelLetters    = document.getElementById('panel-letters');
const panelInterviews = document.getElementById('panel-interviews');
const panelJobs       = document.getElementById('panel-jobs');

const lettersList    = document.getElementById('letters-list');
const interviewsList = document.getElementById('interviews-list');
const jobsList       = document.getElementById('jobs-list');

const emptyLetters    = document.getElementById('empty-letters');
const emptyInterviews = document.getElementById('empty-interviews');
const emptyJobs       = document.getElementById('empty-jobs');

const countLetters    = document.getElementById('count-letters');
const countInterviews = document.getElementById('count-interviews');
const countJobs       = document.getElementById('count-jobs');

const detailOverlay = document.getElementById('detail-overlay');
const detailClose   = document.getElementById('detail-close');
const detailTitle   = document.getElementById('detail-title');
const detailMeta    = document.getElementById('detail-meta');
const detailBody    = document.getElementById('detail-body');

// ---------------------------------------------------------------------------
// Auth guard
// ---------------------------------------------------------------------------
if (!isLoggedIn()) {
    authRequired.hidden  = false;
    historyContent.hidden = true;
} else {
    authRequired.hidden  = true;
    historyContent.hidden = false;
    loadLetters();
    loadInterviews();
    loadJobs();
}

// ---------------------------------------------------------------------------
// Tabs (DRY single handler)
// ---------------------------------------------------------------------------
const tabs = [
    { tab: tabLetters,    panel: panelLetters },
    { tab: tabInterviews, panel: panelInterviews },
    { tab: tabJobs,       panel: panelJobs },
];

function switchTab(activeTab, activePanel) {
    tabs.forEach(({ tab, panel }) => {
        tab.classList.toggle('active', tab === activeTab);
        panel.hidden = panel !== activePanel;
    });
}

tabLetters.addEventListener('click',    () => switchTab(tabLetters,    panelLetters));
tabInterviews.addEventListener('click', () => switchTab(tabInterviews, panelInterviews));
tabJobs.addEventListener('click',       () => switchTab(tabJobs,       panelJobs));

// ---------------------------------------------------------------------------
// Detail overlay
// ---------------------------------------------------------------------------
function openDetail(title, metaHtml, bodyHtml) {
    detailTitle.textContent = title;
    detailMeta.innerHTML    = metaHtml;
    detailBody.innerHTML    = bodyHtml;
    detailOverlay.classList.add('active');
}

function closeDetail() {
    detailOverlay.classList.remove('active');
}

detailClose.addEventListener('click', closeDetail);
detailOverlay.addEventListener('click', (e) => { if (e.target === detailOverlay) closeDetail(); });

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
function showListError(container, message) {
    container.innerHTML = `<p class="error-msg" style="color:var(--error,#ff4d6a); padding:1rem;">${escapeHtml(message)}</p>`;
}

// ---------------------------------------------------------------------------
// Cover Letters
// ---------------------------------------------------------------------------
async function loadLetters() {
    try {
        const data = await apiRequest('/api/cover-letters');
        countLetters.textContent = data.length;
        lettersList.innerHTML = '';

        if (data.length === 0) { emptyLetters.hidden = false; return; }
        emptyLetters.hidden = true;

        data.forEach(item => {
            const el = document.createElement('div');
            el.className = 'history-item';
            el.dataset.id = item.id;
            el.innerHTML = `
                <div class="history-item-info">
                    <div class="history-item-title">✍️ ${escapeHtml(item.job_offer_snippet)}</div>
                    <div class="history-item-date">${formatDate(item.created_at)} · ${escapeHtml(item.language)}</div>
                </div>
                <div class="history-item-actions">
                    <button class="btn-delete" data-id="${item.id}" title="Supprimer">🗑</button>
                </div>`;

            el.addEventListener('click', (e) => {
                if (e.target.closest('.btn-delete')) return;
                showLetterDetail(item.id);
            });
            el.querySelector('.btn-delete').addEventListener('click', async (e) => {
                e.stopPropagation();
                if (!confirm('Supprimer cette lettre ?')) return;
                await deleteLetter(item.id);
            });
            lettersList.appendChild(el);
        });

    } catch (err) {
        showListError(lettersList, `Erreur lors du chargement : ${err.message}`);
    }
}

async function showLetterDetail(id) {
    try {
        const data = await apiRequest(`/api/cover-letters/${id}`);
        const bodyHtml = `
            ${data.summary ? `<p style="color:var(--text-muted);margin-bottom:1rem;font-size:0.85rem;font-style:italic;">${escapeHtml(data.summary)}</p>` : ''}
            <div class="letter-display">${escapeHtml(data.letter_body)}</div>`;

        openDetail(
            '✍️ Lettre de motivation',
            `${formatDate(data.created_at)} · ${escapeHtml(data.language)}<br>${escapeHtml(data.job_offer_snippet)}`,
            bodyHtml
        );
    } catch (err) {
        alert(`Erreur lors du chargement : ${err.message}`);
    }
}

async function deleteLetter(id) {
    try {
        await apiRequest(`/api/cover-letters/${id}`, { method: 'DELETE' });
        loadLetters();
    } catch (err) {
        alert(`Erreur lors de la suppression : ${err.message}`);
    }
}

// ---------------------------------------------------------------------------
// Interview Reports
// ---------------------------------------------------------------------------
async function loadInterviews() {
    try {
        const data = await apiRequest('/api/interviews');
        countInterviews.textContent = data.length;
        interviewsList.innerHTML = '';

        if (data.length === 0) { emptyInterviews.hidden = false; return; }
        emptyInterviews.hidden = true;

        data.forEach(item => {
            const el = document.createElement('div');
            el.className = 'history-item';
            el.innerHTML = `
                <div class="history-item-info">
                    <div class="history-item-title">${escapeHtml(item.title)}</div>
                    <div class="history-item-date">${formatDate(item.created_at)}</div>
                </div>
                <div class="history-item-score">${item.score}</div>
                <div class="history-item-actions">
                    <button class="btn-delete" title="Supprimer">🗑</button>
                </div>`;

            el.addEventListener('click', (e) => {
                if (e.target.closest('.btn-delete')) return;
                showInterviewDetail(item.id);
            });
            el.querySelector('.btn-delete').addEventListener('click', async (e) => {
                e.stopPropagation();
                if (!confirm('Supprimer ce rapport ?')) return;
                await deleteInterview(item.id);
            });
            interviewsList.appendChild(el);
        });

    } catch (err) {
        showListError(interviewsList, `Erreur lors du chargement : ${err.message}`);
    }
}

async function showInterviewDetail(id) {
    try {
        const data = await apiRequest(`/api/interviews/${id}`);

        let html = `<div class="score-badge">${data.score}<span class="label">/10</span></div>`;
        html += `<p style="margin-bottom:1.2rem;">${escapeHtml(data.summary)}</p>`;

        if (data.strengths?.length) {
            html += `<div class="feedback-section-detail"><h3>💪 Points forts</h3>`;
            data.strengths.forEach(p => {
                html += `<div class="feedback-point fort">
                    <div class="fp-topic">${escapeHtml(p.topic)}</div>
                    <div class="fp-comment">${escapeHtml(p.comment)}</div>
                </div>`;
            });
            html += `</div>`;
        }

        if (data.improvements?.length) {
            html += `<div class="feedback-section-detail"><h3>📈 Axes d'amélioration</h3>`;
            data.improvements.forEach(p => {
                html += `<div class="feedback-point improve">
                    <div class="fp-topic">${escapeHtml(p.topic)}</div>
                    <div class="fp-comment">${escapeHtml(p.comment)}</div>
                </div>`;
            });
            html += `</div>`;
        }

        if (data.advice) {
            html += `<div class="advice-card">
                <h3 style="font-size:0.9rem;margin-bottom:0.5rem;">💡 Conseil principal</h3>
                <p style="font-size:0.85rem;color:var(--text-muted);line-height:1.6;">${escapeHtml(data.advice)}</p>
            </div>`;
        }

        if (data.visual_report) {
            html += buildVisualReportHtml(data.visual_report);
        }

        openDetail(
            data.title,
            `${formatDate(data.created_at)}<br>${escapeHtml(data.job_offer_snippet)}`,
            html
        );
    } catch (err) {
        alert(`Erreur lors du chargement : ${err.message}`);
    }
}

async function deleteInterview(id) {
    try {
        await apiRequest(`/api/interviews/${id}`, { method: 'DELETE' });
        loadInterviews();
    } catch (err) {
        alert(`Erreur lors de la suppression : ${err.message}`);
    }
}

// ---------------------------------------------------------------------------
// Saved Jobs
// ---------------------------------------------------------------------------
async function loadJobs() {
    try {
        const data = await apiRequest('/api/jobs/saved');
        countJobs.textContent = data.length;
        jobsList.innerHTML = '';

        if (data.length === 0) { emptyJobs.hidden = false; return; }
        emptyJobs.hidden = true;

        data.forEach(item => {
            const el = document.createElement('div');
            el.className = 'history-item';
            el.innerHTML = `
                <div class="history-item-info">
                    <div class="history-item-title">🚀 ${escapeHtml(item.title)}</div>
                    <div class="history-item-date">${escapeHtml(item.company)} · ${escapeHtml(item.location)}</div>
                </div>
                <div class="history-item-actions">
                    <button class="btn-delete" title="Supprimer">🗑</button>
                </div>`;

            el.addEventListener('click', (e) => {
                if (e.target.closest('.btn-delete')) return;
                showJobDetail(item.id);
            });
            el.querySelector('.btn-delete').addEventListener('click', async (e) => {
                e.stopPropagation();
                if (!confirm('Supprimer cette offre ?')) return;
                await deleteJob(item.id);
            });
            jobsList.appendChild(el);
        });

    } catch (err) {
        showListError(jobsList, `Erreur lors du chargement : ${err.message}`);
    }
}

async function showJobDetail(id) {
    try {
        const data = await apiRequest(`/api/jobs/saved/${id}`);

        const bodyHtml = `
            <div class="job-detail-body">
                <div class="job-detail-meta-item">
                    <i class="fas fa-money-bill-wave"></i>
                    <strong>Rémunération :</strong> ${escapeHtml(data.salary || 'Non précisée')}
                </div>
                <div class="description-view">${escapeHtml(data.description)}</div>
                <div class="job-detail-actions">
                    <a href="${escapeHtml(data.redirect_url)}" target="_blank" rel="noopener" class="btn btn-outline">
                        <i class="fas fa-external-link-alt"></i> Voir l'offre originale
                    </a>
                    <button id="btn-generate-from-job" class="btn btn-primary">
                        <i class="fas fa-magic"></i> Générer une lettre
                    </button>
                </div>
            </div>`;

        openDetail(
            "🚀 Offre d'emploi",
            `<strong>${escapeHtml(data.company)}</strong> · ${escapeHtml(data.location)}<br>${formatDate(data.created_at)}`,
            bodyHtml
        );

        // Bind the "Générer une lettre" button via event listener (no inline onclick)
        document.getElementById('btn-generate-from-job').addEventListener('click', () => {
            localStorage.setItem('last_job_offer', data.description);
            window.location.href = '/coverletter';
        });

    } catch (err) {
        alert(`Erreur lors du chargement : ${err.message}`);
    }
}

async function deleteJob(id) {
    try {
        await apiRequest(`/api/jobs/saved/${id}`, { method: 'DELETE' });
        loadJobs();
    } catch (err) {
        alert(`Erreur lors de la suppression : ${err.message}`);
    }
}

// ---------------------------------------------------------------------------
// Visual report HTML builder (shared between interview detail and feedback page)
// ---------------------------------------------------------------------------
function buildVisualReportHtml(vr) {
    const badgeClass = (assessment) =>
        assessment === 'positif' ? 'badge-positif'
        : assessment === 'neutre' ? 'badge-neutre'
        : 'badge-ameliorer';

    return `
        <div class="visual-report-card" style="margin-top:2rem;">
            <h2>📹 Analyse Visuelle (Webcam)</h2>
            <div class="visual-score-row">
                <div class="visual-score-circle">
                    <span class="score-value">${vr.confidence_score}</span>
                    <span class="score-label">/10</span>
                </div>
                <div class="visual-label">Indice de confiance & posture</div>
            </div>
            <div class="visual-impression">${escapeHtml(vr.overall_impression)}</div>
            <div class="visual-observations">
                ${(vr.observations || []).map(obs => `
                    <div class="visual-obs-item">
                        <span class="visual-obs-badge ${badgeClass(obs.assessment)}">${escapeHtml(obs.assessment)}</span>
                        <span class="visual-obs-text"><strong>${escapeHtml(obs.category)}:</strong> ${escapeHtml(obs.observation)}</span>
                    </div>`).join('')}
            </div>
            <div class="visual-recommendations">
                <h3>💡 Recommandations visuelles</h3>
                <ul>${(vr.recommendations || []).map(r => `<li>${escapeHtml(r)}</li>`).join('')}</ul>
            </div>
        </div>`;
}
