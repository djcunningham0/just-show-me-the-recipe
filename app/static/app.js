document.addEventListener("change", function (e) {
    if (e.target.type === "checkbox") {
        e.target.closest("label").classList.toggle("checked", e.target.checked);
    }
});
