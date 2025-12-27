const healthBadge = document.getElementById("health");
const btn = document.getElementById("btnTest");
const menuToggle = document.getElementById("menuToggle");
const sidebar = document.getElementById("sidebar");
const sidebarOverlay = document.getElementById("sidebarOverlay");

function checkHealth() {
  fetch("/api/health")
    .then(r => r.json())
    .then(() => {
      healthBadge.textContent = "OK";
      healthBadge.className = "badge bg-success";
    })
    .catch(() => {
      healthBadge.textContent = "ERROR";
      healthBadge.className = "badge bg-danger";
    });
}

// Toggle sidebar visibility
function toggleSidebar() {
  sidebar.classList.toggle("show");
  sidebarOverlay.classList.toggle("show");
}

// Close sidebar when clicking overlay
sidebarOverlay.addEventListener("click", () => {
  sidebar.classList.remove("show");
  sidebarOverlay.classList.remove("show");
});

// Close sidebar when clicking on a link (mobile)
document.querySelectorAll(".sidebar .nav-link").forEach(link => {
  link.addEventListener("click", () => {
    if (window.innerWidth <= 768) {
      sidebar.classList.remove("show");
      sidebarOverlay.classList.remove("show");
    }
  });
});

// Menu toggle button
menuToggle.addEventListener("click", toggleSidebar);

// Health check on load
btn.addEventListener("click", checkHealth);
checkHealth();
