/**
 * header.js — Injects the shared navigation bar and highlights the active link.
 * Relies on auth.js being loaded first (uses logout()).
 */

document.addEventListener('DOMContentLoaded', () => {
    const headerContainer = document.getElementById('header-container');
    if (!headerContainer) return;

    const navLinks = [
        { href: '/interview',   label: '💬 Coach' },
        { href: '/coverletter', label: '✍️ Lettre' },
        { href: '/jobsearch',   label: '🚀 Jobs' },
        { href: '/history',     label: '📚 Historique' },
    ];

    const currentPath = window.location.pathname;

    const linksHtml = navLinks.map(({ href, label }) => {
        const isActive = currentPath === href || currentPath.startsWith(href + '/');
        return `<a href="${href}" class="nav-link${isActive ? ' active' : ''}">${label}</a>`;
    }).join('');

    headerContainer.innerHTML = `
        <nav class="main-nav glass-card">
            <div class="nav-left">
                <a href="/" class="nav-logo">🧠</a>
            </div>
            <div class="nav-center">
                ${linksHtml}
            </div>
            <div class="nav-right">
                <button id="btn-logout" class="btn-logout"><i class="fas fa-sign-out-alt"></i></button>
            </div>
        </nav>
    `;

    document.getElementById('btn-logout').addEventListener('click', logout);
});
