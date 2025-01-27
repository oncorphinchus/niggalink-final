async function checkAuth() {
    try {
        const response = await fetch('/api/check-auth');
        const data = await response.json();
        if (!data.authenticated) {
            window.location.href = '/login.html';
        }
    } catch (error) {
        console.error('Auth check failed:', error);
        window.location.href = '/login.html';
    }
}

async function login() {
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    const statusDiv = document.getElementById('auth-status');

    try {
        const response = await fetch('/api/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ username, password })
        });

        const data = await response.json();
        if (response.ok) {
            window.location.href = '/';
        } else {
            statusDiv.textContent = data.error;
            statusDiv.className = 'status error';
        }
    } catch (error) {
        statusDiv.textContent = 'Login failed. Please try again.';
        statusDiv.className = 'status error';
    }
}

async function register() {
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    const statusDiv = document.getElementById('auth-status');

    try {
        const response = await fetch('/api/register', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ username, password })
        });

        const data = await response.json();
        if (response.ok) {
            window.location.href = '/';
        } else {
            statusDiv.textContent = data.error;
            statusDiv.className = 'status error';
        }
    } catch (error) {
        statusDiv.textContent = 'Registration failed. Please try again.';
        statusDiv.className = 'status error';
    }
}

function showRegister() {
    const authForm = document.querySelector('.auth-form');
    const title = document.querySelector('h1');
    title.innerHTML = '<i class="fas fa-user-plus"></i> Register';
    authForm.innerHTML = `
        <div class="input-group">
            <input type="text" id="username" placeholder="Username">
        </div>
        <div class="input-group">
            <input type="password" id="password" placeholder="Password">
        </div>
        <button onclick="register()">Register</button>
        <p class="auth-switch">Already have an account? <a href="#" onclick="showLogin()">Login</a></p>
    `;
}

function showLogin() {
    const authForm = document.querySelector('.auth-form');
    const title = document.querySelector('h1');
    title.innerHTML = '<i class="fas fa-user"></i> Login';
    authForm.innerHTML = `
        <div class="input-group">
            <input type="text" id="username" placeholder="Username">
        </div>
        <div class="input-group">
            <input type="password" id="password" placeholder="Password">
        </div>
        <button onclick="login()">Login</button>
        <p class="auth-switch">Don't have an account? <a href="#" onclick="showRegister()">Register</a></p>
    `;
}

// Add auth check to Script.js
document.addEventListener('DOMContentLoaded', () => {
    checkAuth();
});