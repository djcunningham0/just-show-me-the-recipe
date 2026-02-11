document.addEventListener("change", function (e) {
    if (e.target.type === "checkbox" && e.target.closest(".check-item")) {
        e.target.closest(".check-item").classList.toggle("checked", e.target.checked);
    }
});

// Screen Wake Lock
(function () {
    const toggle = document.getElementById("wake-lock-toggle");
    const checkbox = document.getElementById("wake-lock-checkbox");
    if (!toggle || !checkbox || !("wakeLock" in navigator)) return;

    toggle.hidden = false;
    let wakeLock = null;

    async function requestWakeLock() {
        try {
            wakeLock = await navigator.wakeLock.request("screen");
            wakeLock.addEventListener("release", () => { wakeLock = null; });
        } catch {
            checkbox.checked = false;
        }
    }

    function releaseWakeLock() {
        wakeLock?.release();
        wakeLock = null;
    }

    checkbox.addEventListener("change", () => {
        checkbox.checked ? requestWakeLock() : releaseWakeLock();
    });

    document.addEventListener("visibilitychange", () => {
        if (document.visibilityState === "visible" && checkbox.checked && !wakeLock) {
            requestWakeLock();
        }
    });
})();

// Theme toggle
const toggle = document.getElementById("theme-toggle");
function updateToggleIcon() {
    toggle.textContent =
        document.documentElement.dataset.theme === "dark" ? "\u2600\uFE0F" : "\uD83C\uDF19";
}
updateToggleIcon();
toggle.addEventListener("click", function () {
    const next =
        document.documentElement.dataset.theme === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = next;
    localStorage.setItem("theme", next);
    updateToggleIcon();
});
