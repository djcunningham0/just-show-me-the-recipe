// Recipe scaler — fixed multiplier buttons (1/2x, 1x, 2x, 3x)
(function () {
    var dataEl = document.getElementById("recipe-data");
    if (!dataEl) return;

    var data = JSON.parse(dataEl.textContent);
    if (!data.parsedIngredients) return;

    // Only show controls if at least one ingredient has a scalable amount
    var hasScalable = data.parsedIngredients.some(function (ing) {
        return ing.amount != null;
    });
    if (!hasScalable) return;

    var controls = document.getElementById("scale-controls");
    if (!controls) return;
    controls.hidden = false;

    controls.addEventListener("click", function (e) {
        var btn = e.target.closest(".scale-btn");
        if (!btn) return;

        var scale = parseFloat(btn.dataset.scale);

        // Update active button
        controls.querySelector(".active").classList.remove("active");
        btn.classList.add("active");

        updateIngredients(scale);
    });

    function updateIngredients(scale) {
        data.parsedIngredients.forEach(function (parsed, index) {
            var li = document.querySelector('li[data-index="' + index + '"]');
            if (!li) return;
            var textEl = li.querySelector(".ingredient-text");
            if (!textEl) return;

            if (scale === 1 || parsed.amount == null) {
                textEl.textContent = parsed.raw;
                return;
            }

            var scaledAmount = parsed.amount * scale;
            var scaledMax = parsed.amount_max ? parsed.amount_max * scale : null;
            textEl.textContent = formatIngredient(scaledAmount, scaledMax, parsed);
        });
    }

    function formatIngredient(amount, amountMax, parsed) {
        var parts = [];

        if (amountMax != null) {
            parts.push(formatFraction(amount) + "-" + formatFraction(amountMax));
        } else {
            parts.push(formatFraction(amount));
        }

        if (parsed.unit) parts.push(parsed.unit);
        parts.push(parsed.name);
        if (parsed.preparation) parts.push(", " + parsed.preparation);
        if (parsed.comment) parts.push("(" + parsed.comment + ")");

        return parts.join(" ");
    }

    function formatFraction(n) {
        if (n < 0.01) return "0";

        var whole = Math.floor(n);
        var decimal = n - whole;

        if (decimal < 0.01) return whole.toString();

        // Common fractions with tolerance
        var fractions = [
            [1 / 8, "\u215B"],
            [1 / 4, "\u00BC"],
            [1 / 3, "\u2153"],
            [3 / 8, "\u215C"],
            [1 / 2, "\u00BD"],
            [5 / 8, "\u215D"],
            [2 / 3, "\u2154"],
            [3 / 4, "\u00BE"],
            [7 / 8, "\u215E"],
        ];

        for (var i = 0; i < fractions.length; i++) {
            if (Math.abs(decimal - fractions[i][0]) < 0.03) {
                return whole > 0 ? whole + fractions[i][1] : fractions[i][1];
            }
        }

        // Fallback: round to 1 or 2 decimal places
        var rounded = Math.round(n * 100) / 100;
        if (rounded === Math.round(rounded * 10) / 10) {
            return rounded.toFixed(1);
        }
        return rounded.toFixed(2);
    }
})();
