/**
 * Login / Register page logic.
 * Relies on auth.js being loaded first (AUTH_TOKEN_KEY, AUTH_USER_KEY).
 */

// Redirect immediately if already logged in
if (isLoggedIn()) {
    window.location.href = '/';
}

// DOM
const tabLogin     = document.getElementById('tab-login');
const tabRegister  = document.getElementById('tab-register');
const formLogin    = document.getElementById('form-login');
const formRegister = document.getElementById('form-register');
const authError    = document.getElementById('auth-error');

// ---------------------------------------------------------------------------
// Tab switching
// ---------------------------------------------------------------------------
function switchTab(activeTab, activeForm, inactiveTab, inactiveForm) {
    activeTab.classList.add('active');
    inactiveTab.classList.remove('active');
    activeForm.hidden = false;
    inactiveForm.hidden = true;
    authError.hidden = true;
}

tabLogin.addEventListener('click',    () => switchTab(tabLogin, formLogin, tabRegister, formRegister));
tabRegister.addEventListener('click', () => switchTab(tabRegister, formRegister, tabLogin, formLogin));

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
function showError(msg) {
    authError.textContent = msg;
    authError.hidden = false;
}

function setSubmitLoading(btn, loading, label) {
    btn.disabled = loading;
    btn.textContent = loading ? 'Chargement…' : label;
}

function onSuccess(data) {
    setToken(data.token);
    setUsername(data.username);
    window.location.href = '/';
}

// ---------------------------------------------------------------------------
// Login
// ---------------------------------------------------------------------------
formLogin.addEventListener('submit', async (e) => {
    e.preventDefault();
    authError.hidden = true;

    const username = document.getElementById('login-username').value.trim();
    const password = document.getElementById('login-password').value;
    const btn      = formLogin.querySelector('button[type="submit"]');

    if (!username || !password) {
        showError('Veuillez remplir tous les champs.');
        return;
    }

    setSubmitLoading(btn, true, 'Connexion');
    try {
        const data = await apiRequest('/api/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password }),
        });
        onSuccess(data);
    } catch (err) {
        showError(err.message);
    } finally {
        setSubmitLoading(btn, false, 'Connexion');
    }
});

// ---------------------------------------------------------------------------
// Register
// ---------------------------------------------------------------------------
formRegister.addEventListener('submit', async (e) => {
    e.preventDefault();
    authError.hidden = true;

    const username = document.getElementById('register-username').value.trim();
    const email    = document.getElementById('register-email').value.trim();
    const password = document.getElementById('register-password').value;
    const btn      = formRegister.querySelector('button[type="submit"]');

    if (!username || !email || !password) {
        showError('Veuillez remplir tous les champs.');
        return;
    }

    setSubmitLoading(btn, true, 'Créer le compte');
    try {
        const data = await apiRequest('/api/auth/register', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, email, password }),
        });
        onSuccess(data);
    } catch (err) {
        showError(err.message);
    } finally {
        setSubmitLoading(btn, false, 'Créer le compte');
    }
});
