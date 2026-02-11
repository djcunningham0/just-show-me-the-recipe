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

// Recent recipes
(function () {
    const MAX_RECENT = 10;
    const STORAGE_KEY = "recentRecipes";

    function getRecent() {
        try {
            return JSON.parse(localStorage.getItem(STORAGE_KEY)) || [];
        } catch {
            return [];
        }
    }

    // On recipe page: save this recipe
    const recipeEl = document.querySelector(".recipe");
    if (recipeEl) {
        const linkEl = recipeEl.querySelector("h1 a");
        if (linkEl) {
            const url = linkEl.href;
            const title = linkEl.textContent.trim();
            let recent = getRecent().filter((r) => r.url !== url);
            recent.unshift({ url, title });
            recent = recent.slice(0, MAX_RECENT);
            localStorage.setItem(STORAGE_KEY, JSON.stringify(recent));
        }
    }

    // On homepage: render recent list
    const container = document.getElementById("recent-recipes");
    if (container) {
        const recent = getRecent();
        if (recent.length === 0) return;

        const heading = document.createElement("p");
        heading.className = "recent-heading";
        heading.textContent = "Recently Viewed";
        container.appendChild(heading);

        const list = document.createElement("ul");
        list.className = "recent-list";
        for (const { url, title } of recent) {
            const li = document.createElement("li");
            const a = document.createElement("a");
            a.href = "/recipe?url=" + encodeURIComponent(url);
            a.textContent = title;
            li.appendChild(a);
            list.appendChild(li);
        }
        container.appendChild(list);
    }
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
