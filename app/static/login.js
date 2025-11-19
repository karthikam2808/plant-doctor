const container = document.getElementById('container');
const registerBtn = document.getElementById('register');
const loginBtn = document.getElementById('login');

registerBtn.addEventListener('click', () => {
    container.classList.add("active");
});

loginBtn.addEventListener('click', () => {
    container.classList.remove("active");
});

// Select signup form by querySelector and handle submit
const signupForm = document.querySelector('.sign-up form');
signupForm.addEventListener('submit', async (e) => {
    e.preventDefault();

    // Get inputs by name attribute inside signup form
    const username = signupForm.querySelector('input[name="name"]').value;
    const email = signupForm.querySelector('input[name="email"]').value;
    const password = signupForm.querySelector('input[name="password"]').value;

    try {
        const response = await fetch('/signup', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, email, password })
        });

        if (response.ok) {
            alert("Signup successful! Redirecting to homepage...");
            window.location.href = "/static/index.html"; // adjust redirect as needed
        } else {
            const errorData = await response.json();
            alert("Signup failed: " + (errorData.detail || "Unknown error"));
        }
    } catch (err) {
        console.error("Signup error:", err);
        alert("Error during signup");
    }
});

// Select login form by querySelector and handle submit
const loginForm = document.querySelector('.sign-in form');
loginForm.addEventListener('submit', async (e) => {
    e.preventDefault();

    const email = loginForm.querySelector('input[name="email"]').value;
    const password = loginForm.querySelector('input[name="password"]').value;

    try {
        const response = await fetch('/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });

        if (response.ok) {
            alert("Login successful! Redirecting...");
            window.location.href = "/static/index.html"; // adjust redirect as needed
        } else {
            const errorData = await response.json();
            alert("Login failed: " + (errorData.detail || "Unknown error"));
        }
    } catch (err) {
        console.error("Login error:", err);
        alert("Error during login");
    }
});
