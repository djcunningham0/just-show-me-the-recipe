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

    // Fractions of a cup that aren't standard measuring cups (1/4, 1/3, 1/2, 2/3, 3/4, 1).
    // Map fractional part → tbsp/tsp equivalent.
    var CUP_CONVERSIONS = [
        [1 / 8, "2 tbsp"],
        [1 / 6, "2 tbsp + 2 tsp"],
        [3 / 8, "\u00BC cup + 2 tbsp"],
        [5 / 8, "\u00BD cup + 2 tbsp"],
        [5 / 6, "\u2154 cup + 2 tbsp"],
        [7 / 8, "\u00BE cup + 2 tbsp"],
    ];

    // Standard cup fractions — used to check if a tbsp amount maps to a clean cup measure.
    var STANDARD_CUP_FRACS = [
        [1 / 4, "\u00BC"],
        [1 / 3, "\u2153"],
        [1 / 2, "\u00BD"],
        [2 / 3, "\u2154"],
        [3 / 4, "\u00BE"],
    ];

    function isCupUnit(unit) {
        return /^cups?\.?$/i.test((unit || "").trim());
    }

    function isTbspUnit(unit) {
        return /^(tbsps?|tablespoons?)\.?$/i.test((unit || "").trim());
    }

    function isTspUnit(unit) {
        return /^(tsps?|teaspoons?)\.?$/i.test((unit || "").trim());
    }

    function getCupConversion(amount, unit) {
        if (!isCupUnit(unit)) return null;

        var whole = Math.floor(amount);
        var frac = amount - whole;
        if (frac < 0.01) return null;

        for (var i = 0; i < CUP_CONVERSIONS.length; i++) {
            if (Math.abs(frac - CUP_CONVERSIONS[i][0]) < 0.03) {
                var conversion = CUP_CONVERSIONS[i][1];
                if (whole > 0) {
                    conversion =
                        whole + (whole === 1 ? " cup + " : " cups + ") + conversion;
                }
                return conversion;
            }
        }
        return null;
    }

    // Upward: tbsp → cups (16 tbsp = 1 cup), only for clean cup fractions.
    function getTbspToCupConversion(amount, unit) {
        if (!isTbspUnit(unit)) return null;
        if (amount < 4 - 0.3) return null; // minimum 1/4 cup = 4 tbsp

        var cups = amount / 16;
        var whole = Math.floor(cups);
        var frac = cups - whole;

        // Check if it's a whole number of cups
        if (frac < 0.01) {
            return whole + (whole === 1 ? " cup" : " cups");
        }

        // Check for standard fractions
        for (var i = 0; i < STANDARD_CUP_FRACS.length; i++) {
            if (Math.abs(frac - STANDARD_CUP_FRACS[i][0]) < 0.03) {
                var fracStr = STANDARD_CUP_FRACS[i][1];
                if (whole > 0) {
                    return whole + fracStr + (whole >= 1 ? " cups" : " cup");
                }
                return fracStr + " cup";
            }
        }
        return null;
    }

    // Upward: tsp → tbsp (3 tsp = 1 tbsp), only for clean multiples.
    function getTspToTbspConversion(amount, unit) {
        if (!isTspUnit(unit)) return null;
        if (amount < 3 - 0.3) return null; // minimum 1 tbsp = 3 tsp

        var tbsp = amount / 3;
        var rounded = Math.round(tbsp);
        if (Math.abs(tbsp - rounded) > 0.1) return null;

        return rounded + (rounded === 1 ? " tbsp" : " tbsp");
    }

    function getConversion(amount, unit) {
        return (
            getCupConversion(amount, unit) ||
            getTbspToCupConversion(amount, unit) ||
            getTspToTbspConversion(amount, unit)
        );
    }

    function escapeHtml(str) {
        var div = document.createElement("div");
        div.textContent = str;
        return div.innerHTML;
    }

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
            var conversion = getConversion(scaledAmount, parsed.unit);

            if (conversion) {
                textEl.innerHTML = formatIngredientHtml(
                    scaledAmount,
                    scaledMax,
                    parsed,
                    conversion
                );
            } else {
                textEl.textContent = formatIngredient(
                    scaledAmount,
                    scaledMax,
                    parsed
                );
            }
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
        if (parsed.comment) parts.push(parsed.comment);

        return parts.join(" ");
    }

    function formatIngredientHtml(amount, amountMax, parsed, conversion) {
        var amountStr;
        if (amountMax != null) {
            amountStr = formatFraction(amount) + "-" + formatFraction(amountMax);
        } else {
            amountStr = formatFraction(amount);
        }

        var tipLabel =
            escapeHtml(amountStr + (parsed.unit ? " " + parsed.unit : "")) +
            " = " +
            escapeHtml(conversion);

        var tipContent =
            '<span class="conversion-tip" data-tip="' +
            tipLabel +
            '" data-tip-short="= ' +
            escapeHtml(conversion) +
            '">' +
            escapeHtml(amountStr) +
            (parsed.unit ? " " + escapeHtml(parsed.unit) : "") +
            "</span>";

        var rest = [];
        rest.push(parsed.name);
        if (parsed.preparation) rest.push(", " + parsed.preparation);
        if (parsed.comment) rest.push(parsed.comment);

        return tipContent + " " + escapeHtml(rest.join(" "));
    }

    function formatFraction(n) {
        if (n < 0.01) return "0";

        var whole = Math.floor(n);
        var decimal = n - whole;

        if (decimal < 0.01) return whole.toString();

        // Common fractions with tolerance
        var fractions = [
            [1 / 16, "1/16"],
            [1 / 8, "\u215B"],
            [1 / 6, "\u2159"],
            [1 / 4, "\u00BC"],
            [1 / 3, "\u2153"],
            [3 / 8, "\u215C"],
            [1 / 2, "\u00BD"],
            [5 / 8, "\u215D"],
            [2 / 3, "\u2154"],
            [3 / 4, "\u00BE"],
            [5 / 6, "\u215A"],
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
