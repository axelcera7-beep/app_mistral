/**
 * auth.js — Shared authentication helpers + common utilities.
 * Loaded before all other scripts on every page.
 */

const AUTH_TOKEN_KEY = 'auth_token';
const AUTH_USER_KEY  = 'auth_user';

// ---------------------------------------------------------------------------
// Token management
// ---------------------------------------------------------------------------

function getToken()            { return localStorage.getItem(AUTH_TOKEN_KEY); }
function setToken(token)       { localStorage.setItem(AUTH_TOKEN_KEY, token); }
function getUsername()         { return localStorage.getItem(AUTH_USER_KEY) || ''; }
function setUsername(username) { localStorage.setItem(AUTH_USER_KEY, username); }
function isLoggedIn()          { return !!getToken(); }

function removeToken() {
    localStorage.removeItem(AUTH_TOKEN_KEY);
    localStorage.removeItem(AUTH_USER_KEY);
    const bar = document.getElementById('auth-bar');
    if (bar) bar.remove();
}

function handleAuthError() {
    removeToken();
    window.location.href = '/login';
}

// ---------------------------------------------------------------------------
// Fetch helpers
// ---------------------------------------------------------------------------

function getAuthHeaders() {
    const token = getToken();
    return token ? { 'Authorization': `Bearer ${token}` } : {};
}

/**
 * Merge auth header into a fetch init object.
 * Usage: fetch(url, withAuth({ method: 'POST', body: formData }))
 */
function withAuth(init = {}) {
    const token = getToken();
    if (!token) return init;
    return {
        ...init,
        headers: { ...init.headers, 'Authorization': `Bearer ${token}` },
    };
}

/**
 * Centralized fetch wrapper.
 * - Automatically injects the auth header.
 * - On 401 → redirects to /login.
 * - On non-OK → throws an Error with the backend `detail` message.
 * - Returns the parsed JSON body on success.
 */
async function apiRequest(url, init = {}) {
    const response = await fetch(url, withAuth(init));

    if (response.status === 401) {
        handleAuthError();
        throw new Error('Session expirée. Veuillez vous reconnecter.');
    }

    if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(payload.detail || `Erreur ${response.status}`);
    }

    return response.json();
}

// ---------------------------------------------------------------------------
// Logout
// ---------------------------------------------------------------------------

function logout() {
    removeToken();
    window.location.href = '/login';
}

// ---------------------------------------------------------------------------
// Shared DOM utilities
// ---------------------------------------------------------------------------

/**
 * Safely escape a string for insertion into HTML.
 * Prevents XSS when rendering user-provided or API-returned content.
 */
function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str ?? '';
    return div.innerHTML;
}

/**
 * Format an ISO date string to a human-readable French date/time.
 */
function formatDate(isoStr) {
    return new Date(isoStr).toLocaleDateString('fr-FR', {
        day: 'numeric', month: 'long', year: 'numeric',
        hour: '2-digit', minute: '2-digit',
    });
}

/**
 * UTF-8–safe base64 encoding (handles accents & special chars).
 */
function b64Encode(str) {
    return btoa(encodeURIComponent(str).replace(/%([0-9A-F]{2})/g, (_, p) =>
        String.fromCharCode(parseInt(p, 16))
    ));
}

/**
 * UTF-8–safe base64 decoding (reverse of b64Encode).
 */
function b64Decode(b64) {
    return decodeURIComponent(
        atob(b64).split('').map(c => '%' + c.charCodeAt(0).toString(16).padStart(2, '0')).join('')
    );
}

/**
 * Debounce: delays `fn` until `ms` ms after the last call.
 * Prevents accidental double-submissions on buttons.
 */
function debounce(fn, ms = 400) {
    let timer;
    return (...args) => {
        clearTimeout(timer);
        timer = setTimeout(() => fn(...args), ms);
    };
}

// ---------------------------------------------------------------------------
// Auth UI injection — call on every page
// ---------------------------------------------------------------------------

function injectAuthUI() {
    let bar = document.getElementById('auth-bar');
    if (!bar) {
        bar = document.createElement('div');
        bar.id = 'auth-bar';
        document.body.appendChild(bar);
    }
    bar.style.cssText = `
        position: fixed; top: 0; right: 0; z-index: 9999;
        padding: 0.6rem 1.2rem;
        display: flex; align-items: center; gap: 0.8rem;
        font-family: 'Inter', sans-serif; font-size: 0.82rem;
    `;

    if (isLoggedIn()) {
        bar.innerHTML = `
            <span style="color: #8e8e9a;">👤 ${escapeHtml(getUsername())}</span>
            <a href="/history" style="color: #7c5cfc; text-decoration: none; font-weight: 500;">Historique</a>
            <button id="btn-logout" style="
                background: rgba(255,77,106,0.12); color: #ff4d6a; border: 1px solid rgba(255,77,106,0.25);
                border-radius: 6px; padding: 0.3rem 0.8rem; font-family: inherit; font-size: 0.78rem;
                font-weight: 600; cursor: pointer;
            ">Déconnexion</button>
        `;
    } else {
        bar.innerHTML = `
            <a href="/login" style="
                background: rgba(124,92,252,0.12); color: #7c5cfc; border: 1px solid rgba(124,92,252,0.2);
                border-radius: 6px; padding: 0.3rem 0.8rem; text-decoration: none;
                font-weight: 600; font-size: 0.78rem;
            ">Connexion</a>
        `;
    }

    const logoutBtn = document.getElementById('btn-logout');
    if (logoutBtn) logoutBtn.addEventListener('click', logout);
}

document.addEventListener('DOMContentLoaded', injectAuthUI);
