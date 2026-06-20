const API_BASE = "http://localhost:5000/api";

function getToken() { return localStorage.getItem("token"); }
function getUser()  { return JSON.parse(localStorage.getItem("user") || "{}"); }
function setSession(token, user) {
    localStorage.setItem("token", token);
    localStorage.setItem("user", JSON.stringify(user));
}
function clearSession() {
    localStorage.removeItem("token");
    localStorage.removeItem("user");
    window.location.href = "login.html";
}

async function apiCall(endpoint, method = "GET", body = null) {
    const headers = { "Content-Type": "application/json" };
    const token = getToken();
    if (token) headers["Authorization"] = `Bearer ${token}`;
    const config = { method, headers };
    if (body) config.body = JSON.stringify(body);
    const response = await fetch(`${API_BASE}${endpoint}`, config);
    const data = await response.json();
    if (!response.ok) {
        if (response.status === 401) clearSession();
        throw new Error(data.error || "An error occurred");
    }
    return data;
}

function showToast(msg, type = "success") {
    const existing = document.getElementById("__toast");
    if (existing) existing.remove();
    const toast = document.createElement("div");
    toast.id = "__toast";
    toast.style.cssText = `position:fixed;bottom:2rem;right:2rem;padding:1rem 1.5rem;border-radius:8px;
        color:#fff;font-weight:600;z-index:9999;font-size:0.95rem;max-width:350px;
        background:${type === "success" ? "#00d26a" : "#e53e3e"};
        box-shadow:0 4px 20px rgba(0,0,0,0.4);animation:slideIn 0.3s ease;`;
    toast.innerText = msg;
    const style = document.createElement("style");
    style.innerText = "@keyframes slideIn{from{transform:translateY(100px);opacity:0}to{transform:translateY(0);opacity:1}}";
    document.head.appendChild(style);
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 3500);
}

function showLoading(btnEl, loading = true, label = "Submit") {
    if (loading) { btnEl.disabled = true; btnEl.innerHTML = `<span class="spinner"></span> Loading...`; }
    else          { btnEl.disabled = false; btnEl.innerText = label; }
}
