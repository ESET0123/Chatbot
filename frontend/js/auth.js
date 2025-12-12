const API_URL = "http://127.0.0.1:8000";

// Show / Hide error message
function showError(message) {
  const errorDiv = document.getElementById("errorMessage");
  errorDiv.textContent = message;
  errorDiv.classList.add("show");
}

function hideError() {
  document.getElementById("errorMessage").classList.remove("show");
}

// Tab switching logic
document.querySelectorAll(".tab-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    const tab = btn.dataset.tab;

    document.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("active"));
    document.querySelectorAll(".form-tab").forEach((f) => f.classList.remove("active"));

    btn.classList.add("active");
    document.getElementById(tab + "Form").classList.add("active");

    hideError();
  });
});

// LOGIN HANDLER
document.getElementById("loginFormElement").addEventListener("submit", async (e) => {
  e.preventDefault();
  hideError();

  const email = document.getElementById("loginEmail").value;
  const password = document.getElementById("loginPassword").value;
  const btn = document.getElementById("loginBtn");

  btn.disabled = true;
  btn.textContent = "Logging in...";

  try {
    const res = await fetch(`${API_URL}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });

    const data = await res.json();

    if (!res.ok) {
      showError(data.detail || "Login failed");
      btn.disabled = false;
      btn.textContent = "Login";
      return;
    }

    sessionStorage.setItem("token", data.access_token);
    sessionStorage.setItem(
      "user",
      JSON.stringify({
        id: data.user_id,
        name: data.name || "User",
        email: data.email,
        role: data.role || "user",
      })
    );

    window.location.href = "./../frontend/index.html";
  } catch (err) {
    console.error(err);
    showError("Connection error. Please try again.");
  }

  btn.disabled = false;
  btn.textContent = "Login";
});

// REGISTER HANDLER
document.getElementById("registerFormElement").addEventListener("submit", async (e) => {
  e.preventDefault();
  hideError();

  const name = document.getElementById("registerName").value.trim();
  const email = document.getElementById("registerEmail").value.trim();
  const password = document.getElementById("registerPassword").value;
  const role = document.getElementById("registerRole").value;
  const btn = document.getElementById("registerBtn");

  if (!name) {
    showError("Please enter your full name");
    return;
  }

  if (password.length < 6) {
    showError("Password must be at least 6 characters");
    return;
  }

  btn.disabled = true;
  btn.textContent = "Creating...";

  try {
    const res = await fetch(`${API_URL}/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, email, password, role }),
    });

    const data = await res.json();

    if (!res.ok) {
      showError(data.detail || "Registration failed");
      btn.disabled = false;
      btn.textContent = "Create Account";
      return;
    }

    sessionStorage.setItem("token", data.access_token);
    sessionStorage.setItem(
      "user",
      JSON.stringify({
        id: data.user_id,
        name: data.name,
        email: data.email,
        role: data.role,
      })
    );

    window.location.href = "./../frontend/index.html";
  } catch (err) {
    console.error("Registration error:", err);
    showError("Connection error. Please try again.");
  }

  btn.disabled = false;
  btn.textContent = "Create Account";
});

// Auto-redirect if already logged in
if (sessionStorage.getItem("token")) {
  window.location.href = "./../frontend/index.html";
}
