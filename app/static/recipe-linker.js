// Recipe linker — bidirectional ingredient-to-step highlighting
(function () {
    var dataEl = document.getElementById("recipe-data");
    if (!dataEl) return;

    var data = JSON.parse(dataEl.textContent);
    if (!data.parsedIngredients || !data.steps) return;

    var ingredients = data.parsedIngredients;
    var ingredientEls = document.querySelectorAll("li[data-index]");
    var stepEls = document.querySelectorAll("li[data-step-idx]");
    if (!ingredientEls.length || !stepEls.length) return;

    // --- Toggle state ---

    var STORAGE_KEY = "highlightIngredients";
    var toggleCheckbox = document.getElementById("highlight-toggle-checkbox");
    var enabled = false;

    if (toggleCheckbox) {
        enabled = localStorage.getItem(STORAGE_KEY) === "true";
        toggleCheckbox.checked = enabled;
        toggleCheckbox.addEventListener("change", function () {
            enabled = toggleCheckbox.checked;
            localStorage.setItem(STORAGE_KEY, enabled);
            if (enabled) {
                activate();
            } else {
                deactivate();
            }
        });
    }

    // --- Matching helpers ---

    var MODIFIERS = [
        "salted", "unsalted", "dried", "fresh", "freshly", "cracked",
        "crushed", "ground", "light", "dark", "all purpose", "all-purpose",
        "granulated", "powdered", "confectioners", "packed", "large",
        "medium", "small", "extra virgin", "extra-virgin", "pure", "raw",
        "organic", "whole", "boneless", "skinless", "frozen", "canned",
        "toasted", "roasted", "smoked", "sharp", "mild", "sweet", "plain",
        "heavy", "white", "low-fat", "nonfat", "reduced-fat",
    ];

    MODIFIERS.sort(function (a, b) {
        return b.length - a.length;
    });

    function stripModifiers(name) {
        var result = name;
        for (var i = 0; i < MODIFIERS.length; i++) {
            var escaped = MODIFIERS[i].replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
            var re = new RegExp("\\b" + escaped + "\\b\\s*", "g");
            result = result.replace(re, "");
        }
        return result.trim();
    }

    function pluralVariants(word) {
        var variants = [word];
        if (word.endsWith("s")) {
            variants.push(word.slice(0, -1));
        }
        if (word.endsWith("es")) {
            variants.push(word.slice(0, -2));
        }
        if (word.endsWith("ies")) {
            variants.push(word.slice(0, -3) + "y");
        }
        if (!word.endsWith("s")) {
            variants.push(word + "s");
            variants.push(word + "es");
        }
        if (word.endsWith("y") && !word.endsWith("ey")) {
            variants.push(word.slice(0, -1) + "ies");
        }
        return variants;
    }

    // Alternate spellings: each word maps to its known variants
    var SPELLING_VARIANTS = {
        "chili": ["chilli", "chile"],
        "chilli": ["chili", "chile"],
        "chile": ["chili", "chilli"],
        "yogurt": ["yoghurt"],
        "yoghurt": ["yogurt"],
    };

    // Generate alternate spellings for a phrase by substituting known variants
    function spellingVariants(phrase) {
        var words = phrase.split(/\s+/);
        var results = [];
        for (var i = 0; i < words.length; i++) {
            var alts = SPELLING_VARIANTS[words[i]];
            if (alts) {
                for (var a = 0; a < alts.length; a++) {
                    var copy = words.slice();
                    copy[i] = alts[a];
                    results.push(copy.join(" "));
                }
            }
        }
        return results;
    }

    var AMBIGUOUS_COMPOUNDS = {
        "pepper": ["bell", "cayenne", "chili", "chile", "jalape", "salt and"],
        "powder": ["cocoa", "baking", "garlic", "onion", "curry", "mustard",
            "ginger", "turmeric", "cayenne", "paprika", "cumin", "cinnamon",
            "chili", "chilli", "chile", "chipotle"],
        "cream": ["ice"],
        "sauce": ["hot"],
        "oil": ["essential"],
    };

    function isAmbiguousMatch(text, word, matchIndex) {
        var baseWord = word.replace(/e?s$/, "");
        var prefixes = AMBIGUOUS_COMPOUNDS[word] || AMBIGUOUS_COMPOUNDS[baseWord];
        if (!prefixes) return false;
        var before = text.slice(0, matchIndex);
        return prefixes.some(function (prefix) {
            return new RegExp("\\b" + prefix + "\\s+$").test(before);
        });
    }

    function buildVariants(name) {
        var candidates = [name];

        var coreName = stripModifiers(name);
        if (coreName !== name && coreName.length >= 3) {
            candidates.push(coreName);
        }

        var words = coreName.split(/\s+/);
        if (words.length >= 2) {
            var tail = words.slice(1).join(" ");
            if (tail.length >= 3) {
                candidates.push(tail);
            }
            var head = words.slice(0, -1).join(" ");
            if (head.length >= 3) {
                candidates.push(head);
            }
        }
        if (words.length >= 3) {
            var lastWord = words[words.length - 1];
            if (lastWord.length >= 3) {
                candidates.push(lastWord);
            }
            var firstWord = words[0];
            if (firstWord.length >= 3) {
                candidates.push(firstWord);
            }
        }

        // Add alternate spellings for each candidate
        var expanded = candidates.slice();
        for (var s = 0; s < candidates.length; s++) {
            var sv = spellingVariants(candidates[s]);
            for (var t = 0; t < sv.length; t++) {
                expanded.push(sv[t]);
            }
        }

        var allVariants = [];
        for (var i = 0; i < expanded.length; i++) {
            var pv = pluralVariants(expanded[i]);
            for (var j = 0; j < pv.length; j++) {
                allVariants.push(pv[j]);
            }
        }

        var seen = {};
        return allVariants.filter(function (v) {
            if (v.length < 3 || seen[v]) return false;
            seen[v] = true;
            return true;
        });
    }

    // --- Inline highlighting helpers ---

    function escapeHTML(text) {
        return text
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;");
    }

    // Find all match positions for a set of variants in text (case-insensitive).
    // Returns sorted, non-overlapping [{start, end}] preferring longer matches.
    function findMatchPositions(text, variants) {
        var lowerText = text.toLowerCase();
        var raw = [];
        for (var i = 0; i < variants.length; i++) {
            var escaped = variants[i].replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
            var re = new RegExp("\\b" + escaped + "\\b", "gi");
            var match;
            while ((match = re.exec(lowerText)) !== null) {
                if (isAmbiguousMatch(lowerText, variants[i], match.index)) continue;
                raw.push({
                    start: match.index,
                    end: match.index + match[0].length,
                    len: match[0].length,
                });
            }
        }
        // Sort by length desc so longer matches win, then by start asc
        raw.sort(function (a, b) {
            return b.len - a.len || a.start - b.start;
        });
        // Greedily pick non-overlapping matches
        var taken = [];
        for (var k = 0; k < raw.length; k++) {
            var overlaps = false;
            for (var t = 0; t < taken.length; t++) {
                if (raw[k].start < taken[t].end && raw[k].end > taken[t].start) {
                    overlaps = true;
                    break;
                }
            }
            if (!overlaps) taken.push(raw[k]);
        }
        taken.sort(function (a, b) {
            return a.start - b.start;
        });
        return taken;
    }

    // Build HTML with <mark> tags around matched positions.
    // `originalText` is the raw text (not HTML-escaped); positions index into it.
    function buildHighlightedHTML(originalText, positions) {
        if (!positions.length) return escapeHTML(originalText);
        var html = "";
        var last = 0;
        for (var i = 0; i < positions.length; i++) {
            html += escapeHTML(originalText.slice(last, positions[i].start));
            html +=
                '<mark class="ing-highlight">' +
                escapeHTML(
                    originalText.slice(positions[i].start, positions[i].end),
                ) +
                "</mark>";
            last = positions[i].end;
        }
        html += escapeHTML(originalText.slice(last));
        return html;
    }

    // Get the text <span> inside a step <li> (the second span inside .check-item)
    function getStepTextSpan(stepEl) {
        var spans = stepEl.querySelectorAll(".check-item > span");
        return spans.length ? spans[spans.length - 1] : null;
    }

    // --- Build matching index ---

    var ingredientToSteps = [];
    var stepToIngredients = [];
    var ingredientVariants = {}; // idx -> variants array
    var i, j;

    for (i = 0; i < ingredients.length; i++) {
        ingredientToSteps.push([]);
    }
    for (j = 0; j < data.steps.length; j++) {
        stepToIngredients.push([]);
    }

    var nameData = [];
    for (i = 0; i < ingredients.length; i++) {
        var name = (ingredients[i].name || "").toLowerCase().trim();
        if (name.length < 3) continue;

        var variants = buildVariants(name);
        nameData.push({ idx: i, name: name, variants: variants, len: name.length });
        ingredientVariants[i] = variants;
    }
    nameData.sort(function (a, b) {
        return b.len - a.len;
    });

    for (j = 0; j < data.steps.length; j++) {
        var stepText = data.steps[j].toLowerCase();
        for (i = 0; i < nameData.length; i++) {
            var nd = nameData[i];
            if (findMatchPositions(stepText, nd.variants).length) {
                ingredientToSteps[nd.idx].push(j);
                stepToIngredients[j].push(nd.idx);
            }
        }
    }

    // Store original step text so we can restore after highlighting
    var originalStepText = {};
    stepEls.forEach(function (el) {
        var idx = parseInt(el.dataset.stepIdx, 10);
        var span = getStepTextSpan(el);
        if (span) originalStepText[idx] = span.textContent;
    });

    // --- Event handling ---

    var hasHover =
        window.matchMedia && window.matchMedia("(hover: hover)").matches;

    var activeIngredient = -1;
    var activeStep = -1;
    // Store bound handlers so we can remove them on deactivate
    var boundHandlers = [];

    // Apply inline <mark> highlights to a step for a set of ingredient indices
    function applyInlineHighlights(stepIdx, ingIndices) {
        var span = getStepTextSpan(stepEls[stepIdx]);
        if (!span || !(stepIdx in originalStepText)) return;
        var text = originalStepText[stepIdx];
        // Collect all variants across requested ingredients
        var allVariants = [];
        for (var i = 0; i < ingIndices.length; i++) {
            var v = ingredientVariants[ingIndices[i]];
            if (!v) continue;
            for (var j = 0; j < v.length; j++) {
                allVariants.push(v[j]);
            }
        }
        var positions = findMatchPositions(text, allVariants);
        span.innerHTML = buildHighlightedHTML(text, positions);
    }

    function restoreStepText(stepIdx) {
        var span = getStepTextSpan(stepEls[stepIdx]);
        if (!span || !(stepIdx in originalStepText)) return;
        span.textContent = originalStepText[stepIdx];
    }

    function highlightIngredient(idx) {
        ingredientEls[idx].classList.add("linked-highlight");
        ingredientToSteps[idx].forEach(function (stepIdx) {
            stepEls[stepIdx].classList.add("linked-highlight-step");
            applyInlineHighlights(stepIdx, [idx]);
        });
    }

    function highlightStep(idx) {
        var ingIndices = stepToIngredients[idx];
        ingIndices.forEach(function (ingIdx) {
            ingredientEls[ingIdx].classList.add("linked-highlight");
        });
        stepEls[idx].classList.add("linked-highlight-step");
        applyInlineHighlights(idx, ingIndices);
    }

    function clearHighlights() {
        document.querySelectorAll(".linked-highlight").forEach(function (el) {
            el.classList.remove("linked-highlight");
        });
        document
            .querySelectorAll(".linked-highlight-step")
            .forEach(function (el) {
                el.classList.remove("linked-highlight-step");
                var idx = parseInt(el.dataset.stepIdx, 10);
                restoreStepText(idx);
            });
    }

    function toggleIngredient(idx) {
        if (activeIngredient === idx) {
            clearHighlights();
            activeIngredient = -1;
            activeStep = -1;
            return;
        }
        clearHighlights();
        activeStep = -1;
        activeIngredient = idx;
        highlightIngredient(idx);
    }

    function toggleStep(idx) {
        if (activeStep === idx) {
            clearHighlights();
            activeStep = -1;
            activeIngredient = -1;
            return;
        }
        clearHighlights();
        activeIngredient = -1;
        activeStep = idx;
        highlightStep(idx);
    }

    function activate() {
        ingredientEls.forEach(function (el) {
            var idx = parseInt(el.dataset.index, 10);
            if (!ingredientToSteps[idx] || !ingredientToSteps[idx].length) return;

            el.classList.add("linkable");

            if (hasHover) {
                var enter = function () { highlightIngredient(idx); };
                var leave = function () { clearHighlights(); };
                el.addEventListener("mouseenter", enter);
                el.addEventListener("mouseleave", leave);
                boundHandlers.push({ el: el, type: "mouseenter", fn: enter });
                boundHandlers.push({ el: el, type: "mouseleave", fn: leave });
            } else {
                var click = function (e) {
                    if (e.target.tagName === "INPUT") return;
                    e.preventDefault();
                    toggleIngredient(idx);
                };
                el.addEventListener("click", click);
                boundHandlers.push({ el: el, type: "click", fn: click });
            }
        });

        stepEls.forEach(function (el) {
            var idx = parseInt(el.dataset.stepIdx, 10);
            if (!stepToIngredients[idx] || !stepToIngredients[idx].length) return;

            el.classList.add("linkable");

            if (hasHover) {
                var enter = function () { highlightStep(idx); };
                var leave = function () { clearHighlights(); };
                el.addEventListener("mouseenter", enter);
                el.addEventListener("mouseleave", leave);
                boundHandlers.push({ el: el, type: "mouseenter", fn: enter });
                boundHandlers.push({ el: el, type: "mouseleave", fn: leave });
            } else {
                var click = function (e) {
                    if (e.target.tagName === "INPUT") return;
                    e.preventDefault();
                    toggleStep(idx);
                };
                el.addEventListener("click", click);
                boundHandlers.push({ el: el, type: "click", fn: click });
            }
        });
    }

    function deactivate() {
        clearHighlights();
        activeIngredient = -1;
        activeStep = -1;

        // Remove all event listeners
        boundHandlers.forEach(function (h) {
            h.el.removeEventListener(h.type, h.fn);
        });
        boundHandlers = [];

        // Remove linkable class
        document.querySelectorAll(".linkable").forEach(function (el) {
            el.classList.remove("linkable");
        });
    }

    // Initialize if enabled
    if (enabled) {
        activate();
    }
})();
