/**
 * jobsearch.js — Job search with CV matching and pagination.
 * Relies on auth.js (apiRequest, withAuth, getToken, handleAuthError, escapeHtml, b64Encode, b64Decode).
 */

document.addEventListener('DOMContentLoaded', () => {

    // Auth guard — redirect to login if not authenticated
    if (!isLoggedIn()) {
        window.location.href = '/login?redirect=/jobsearch';
        return;
    }

    // ---------------------------------------------------------------------------
    // DOM
    // ---------------------------------------------------------------------------
    const searchForm   = document.getElementById('search-form');
    const resultsSection = document.getElementById('results-section');
    const loading      = document.getElementById('loading');
    const searchBtn    = document.getElementById('search-btn');
    const cvUpload     = document.getElementById('cv-upload');
    const cvUploadBtn  = document.getElementById('cv-upload-btn');
    const cvStatus     = document.getElementById('cv-status');
    const cvFilename   = document.getElementById('cv-filename');
    const clearCvBtn   = document.getElementById('clear-cv');
    const cvTextInput  = document.getElementById('cv-text-input');

    // ---------------------------------------------------------------------------
    // State
    // ---------------------------------------------------------------------------
    let selectedFile = null;
    const jobRegistry = new Map(); // id → job object
    let allJobs = [];              // full results from API
    let currentPage = 1;
    const JOBS_PER_PAGE = 10;

    // ---------------------------------------------------------------------------
    // CV Upload
    // ---------------------------------------------------------------------------
    cvUploadBtn.addEventListener('click', () => cvUpload.click());

    cvUpload.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (!file) return;
        selectedFile = file;
        cvFilename.textContent = file.name;
        cvStatus.classList.remove('hidden');
        cvUploadBtn.classList.add('hidden');
        cvTextInput.classList.add('hidden');
    });

    clearCvBtn.addEventListener('click', () => {
        selectedFile = null;
        cvUpload.value = '';
        cvStatus.classList.add('hidden');
        cvUploadBtn.classList.remove('hidden');
        cvTextInput.classList.remove('hidden');
    });

    // ---------------------------------------------------------------------------
    // Search
    // ---------------------------------------------------------------------------
    searchForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        const keywords    = document.getElementById('keywords').value.trim();
        const location    = document.getElementById('location').value.trim();
        const manualCvText = cvTextInput.value.trim();

        const formData = new FormData();
        formData.append('keywords', keywords);
        formData.append('location', location);

        if (selectedFile) {
            formData.append('cv_file', selectedFile);
        } else if (manualCvText) {
            formData.append('cv_text', manualCvText);
        }

        loading.classList.remove('hidden');
        resultsSection.innerHTML = '';
        searchBtn.disabled = true;

        try {
            const data = await apiRequest('/api/jobs/search', withAuth({ method: 'POST', body: formData }));
            allJobs = data.results || [];
            currentPage = 1;
            renderPage();
        } catch (err) {
            resultsSection.innerHTML = `<p class="error-msg">Erreur : ${escapeHtml(err.message)}</p>`;
        } finally {
            loading.classList.add('hidden');
            searchBtn.disabled = false;
        }
    });

    // ---------------------------------------------------------------------------
    // Pagination logic
    // ---------------------------------------------------------------------------
    function getTotalPages() {
        return Math.max(1, Math.ceil(allJobs.length / JOBS_PER_PAGE));
    }

    function getPageJobs() {
        const start = (currentPage - 1) * JOBS_PER_PAGE;
        return allJobs.slice(start, start + JOBS_PER_PAGE);
    }

    function goToPage(page) {
        const total = getTotalPages();
        currentPage = Math.max(1, Math.min(page, total));
        renderPage();
        // Scroll to top of results
        resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    // ---------------------------------------------------------------------------
    // Render
    // ---------------------------------------------------------------------------
    function renderPage() {
        jobRegistry.clear();
        resultsSection.innerHTML = '';

        if (!allJobs.length) {
            resultsSection.innerHTML = '<div class="glass-card no-results">Aucune offre trouvée pour ces critères.</div>';
            return;
        }

        // Results count
        const countBar = document.createElement('div');
        countBar.className = 'results-count';
        countBar.innerHTML = `<i class="fas fa-briefcase"></i> ${allJobs.length} offre${allJobs.length > 1 ? 's' : ''} trouvée${allJobs.length > 1 ? 's' : ''}`;
        resultsSection.appendChild(countBar);

        // Job cards for current page
        const pageJobs = getPageJobs();
        const cardsContainer = document.createElement('div');
        cardsContainer.className = 'results-cards';
        cardsContainer.innerHTML = pageJobs.map(job => {
            jobRegistry.set(job.id, job);
            const matchBadge = job.match_score != null
                ? `<div class="match-badge ${getMatchClass(job.match_score)}"><i class="fas fa-bullseye"></i> ${job.match_score}% match</div>`
                : '';
            return `
                <div class="job-card glass-card animate-fade-in" data-job-id="${escapeHtml(job.id)}">
                    <div class="job-header">
                        <div class="job-title-group">
                            <h3>${escapeHtml(job.title)}</h3>
                            <p class="company">${escapeHtml(job.company)} • ${escapeHtml(job.location)}</p>
                        </div>
                        ${matchBadge}
                    </div>
                    <div class="job-body">
                        <p class="description">${escapeHtml(stripHtml(job.description).substring(0, 250))}…</p>
                    </div>
                    <div class="job-footer">
                        <span class="job-date"><i class="fas fa-calendar-alt"></i> ${formatDate(job.created)}</span>
                        <span class="salary"><i class="fas fa-money-bill-wave"></i> ${escapeHtml(job.salary || 'N/A')}</span>
                        <div class="actions">
                            <button class="btn btn-outline btn-sm btn-save" title="Sauvegarder l'offre">
                                <i class="fas fa-bookmark"></i> Sauvegarder
                            </button>
                            <a href="${escapeHtml(job.redirect_url)}" target="_blank" rel="noopener" class="btn btn-outline btn-sm">Voir l'offre</a>
                            <button class="btn btn-primary btn-sm btn-letter">Préparer la lettre</button>
                        </div>
                    </div>
                </div>`;
        }).join('');
        resultsSection.appendChild(cardsContainer);

        // Pagination controls
        const totalPages = getTotalPages();
        if (totalPages > 1) {
            resultsSection.appendChild(buildPagination(totalPages));
        }

        // Event delegation
        cardsContainer.addEventListener('click', onResultClick);
    }

    function buildPagination(totalPages) {
        const nav = document.createElement('nav');
        nav.className = 'pagination';

        // Previous button
        const prevBtn = document.createElement('button');
        prevBtn.className = 'pagination-btn pagination-prev';
        prevBtn.disabled = currentPage === 1;
        prevBtn.innerHTML = '<i class="fas fa-chevron-left"></i> Précédent';
        prevBtn.addEventListener('click', () => goToPage(currentPage - 1));
        nav.appendChild(prevBtn);

        // Page numbers
        const pages = document.createElement('div');
        pages.className = 'pagination-pages';

        const pageNumbers = getVisiblePages(currentPage, totalPages);
        for (const p of pageNumbers) {
            if (p === '...') {
                const ellipsis = document.createElement('span');
                ellipsis.className = 'pagination-ellipsis';
                ellipsis.textContent = '…';
                pages.appendChild(ellipsis);
            } else {
                const btn = document.createElement('button');
                btn.className = 'pagination-btn pagination-num' + (p === currentPage ? ' active' : '');
                btn.textContent = p;
                btn.addEventListener('click', () => goToPage(p));
                pages.appendChild(btn);
            }
        }
        nav.appendChild(pages);

        // Next button
        const nextBtn = document.createElement('button');
        nextBtn.className = 'pagination-btn pagination-next';
        nextBtn.disabled = currentPage === totalPages;
        nextBtn.innerHTML = 'Suivant <i class="fas fa-chevron-right"></i>';
        nextBtn.addEventListener('click', () => goToPage(currentPage + 1));
        nav.appendChild(nextBtn);

        return nav;
    }

    function getVisiblePages(current, total) {
        if (total <= 7) return Array.from({ length: total }, (_, i) => i + 1);

        const pages = [];
        pages.push(1);

        if (current > 3) pages.push('...');

        const start = Math.max(2, current - 1);
        const end = Math.min(total - 1, current + 1);
        for (let i = start; i <= end; i++) pages.push(i);

        if (current < total - 2) pages.push('...');

        pages.push(total);
        return pages;
    }

    // ---------------------------------------------------------------------------
    // Event handlers
    // ---------------------------------------------------------------------------
    function onResultClick(e) {
        const card = e.target.closest('[data-job-id]');
        if (!card) return;
        const job = jobRegistry.get(card.dataset.jobId);
        if (!job) return;

        if (e.target.closest('.btn-save')) {
            saveJob(job);
        } else if (e.target.closest('.btn-letter')) {
            localStorage.setItem('last_job_offer', job.description);
            window.location.href = '/coverletter';
        }
    }

    // ---------------------------------------------------------------------------
    // Save a job offer
    // ---------------------------------------------------------------------------
    async function saveJob(job) {
        try {
            const data = await apiRequest('/api/jobs/save', withAuth({
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    external_id: job.id,
                    title:       job.title,
                    company:     job.company,
                    location:    job.location,
                    description: job.description,
                    salary:      job.salary,
                    redirect_url: job.redirect_url,
                }),
            }));
            alert(data.detail || 'Offre sauvegardée !');
        } catch (err) {
            alert(`Erreur lors de la sauvegarde : ${err.message}`);
        }
    }

    // ---------------------------------------------------------------------------
    // Helpers
    // ---------------------------------------------------------------------------
    function getMatchClass(score) {
        if (score >= 80) return 'match-high';
        if (score >= 60) return 'match-medium';
        return 'match-low';
    }

    function formatDate(dateStr) {
        if (!dateStr) return 'Date inconnue';
        try {
            const d = new Date(dateStr);
            if (isNaN(d.getTime())) return 'Date inconnue';
            return d.toLocaleDateString('fr-FR', { day: 'numeric', month: 'long', year: 'numeric' });
        } catch {
            return 'Date inconnue';
        }
    }

    function stripHtml(html) {
        const tmp = document.createElement('div');
        tmp.innerHTML = html;
        return tmp.textContent || tmp.innerText || '';
    }
});
