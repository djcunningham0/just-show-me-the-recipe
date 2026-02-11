document.addEventListener("change", function (e) {
    if (e.target.type === "checkbox") {
        e.target.closest(".check-item").classList.toggle("checked", e.target.checked);
    }
});

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
