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

    // --- Matching helpers (must be defined before use) ---

    // Modifiers that commonly prefix ingredient names but get dropped in
    // recipe instructions. Curated from ingredient_parser's tagdict
    // (JJ/VBN/RB categories). Excludes colors like "red", "black", "green"
    // that are often essential to identity (e.g., "red pepper" ≠ "pepper").
    var MODIFIERS = [
        "salted", "unsalted", "dried", "fresh", "freshly", "cracked",
        "crushed", "ground", "light", "dark", "all purpose", "all-purpose",
        "granulated", "powdered", "confectioners", "packed", "large",
        "medium", "small", "extra virgin", "extra-virgin", "pure", "raw",
        "organic", "whole", "boneless", "skinless", "frozen", "canned",
        "toasted", "roasted", "smoked", "sharp", "mild", "sweet", "plain",
        "heavy", "white", "low-fat", "nonfat", "reduced-fat",
    ];

    // Sort longest-first so "all purpose" is stripped before "all"
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

    // Words that form different ingredients when preceded by certain
    // qualifiers. Bare "pepper" still matches, but not when preceded by
    // "bell" (which is a different ingredient). This avoids false positives
    // while preserving true positives like "freshly cracked pepper".
    var AMBIGUOUS_COMPOUNDS = {
        "pepper": ["bell", "cayenne", "chili", "chile", "jalape"],
        "cream": ["ice"],
        "sauce": ["hot"],
        "oil": ["essential"],
    };

    function buildVariants(name) {
        var candidates = [name];

        // Strip modifiers to get core name
        var coreName = stripModifiers(name);
        if (coreName !== name && coreName.length >= 3) {
            candidates.push(coreName);
        }

        // Sub-phrases from core name (drop leading or trailing words)
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

        // Generate plural/singular variants for each candidate
        var allVariants = [];
        for (var i = 0; i < candidates.length; i++) {
            var pv = pluralVariants(candidates[i]);
            for (var j = 0; j < pv.length; j++) {
                allVariants.push(pv[j]);
            }
        }

        // Deduplicate, filter short strings
        var seen = {};
        return allVariants.filter(function (v) {
            if (v.length < 3 || seen[v]) return false;
            seen[v] = true;
            return true;
        });
    }

    function matchesAny(text, variants) {
        for (var i = 0; i < variants.length; i++) {
            if (wordBoundaryMatch(text, variants[i])) return true;
        }
        return false;
    }

    function wordBoundaryMatch(text, word) {
        var escaped = word.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
        var re = new RegExp("\\b" + escaped + "\\b", "g");
        var match;
        while ((match = re.exec(text)) !== null) {
            // Check if this is a false positive due to a disqualifying prefix
            var baseWord = word.replace(/e?s$/, ""); // normalize plurals
            var prefixes = AMBIGUOUS_COMPOUNDS[word] || AMBIGUOUS_COMPOUNDS[baseWord];
            if (prefixes) {
                var before = text.slice(0, match.index);
                var dominated = prefixes.some(function (prefix) {
                    return new RegExp("\\b" + prefix + "\\s+$").test(before);
                });
                if (dominated) continue;
            }
            return true;
        }
        return false;
    }

    // --- Build matching index ---

    var ingredientToSteps = [];
    var stepToIngredients = [];
    var i, j;

    for (i = 0; i < ingredients.length; i++) {
        ingredientToSteps.push([]);
    }
    for (j = 0; j < data.steps.length; j++) {
        stepToIngredients.push([]);
    }

    // Build name variants sorted longest-first for greedy matching
    var nameData = [];
    for (i = 0; i < ingredients.length; i++) {
        var name = (ingredients[i].name || "").toLowerCase().trim();
        if (name.length < 3) continue;

        var variants = buildVariants(name);
        nameData.push({ idx: i, name: name, variants: variants, len: name.length });
    }
    nameData.sort(function (a, b) {
        return b.len - a.len;
    });

    // Match each step against ingredient names
    for (j = 0; j < data.steps.length; j++) {
        var stepText = data.steps[j].toLowerCase();
        for (i = 0; i < nameData.length; i++) {
            var nd = nameData[i];
            if (matchesAny(stepText, nd.variants)) {
                ingredientToSteps[nd.idx].push(j);
                stepToIngredients[j].push(nd.idx);
            }
        }
    }

    // --- Event handling ---

    var hasHover =
        window.matchMedia && window.matchMedia("(hover: hover)").matches;

    ingredientEls.forEach(function (el) {
        var idx = parseInt(el.dataset.index, 10);
        if (!ingredientToSteps[idx] || !ingredientToSteps[idx].length) return;

        el.classList.add("linkable");

        if (hasHover) {
            el.addEventListener("mouseenter", function () {
                highlightIngredient(idx);
            });
            el.addEventListener("mouseleave", function () {
                clearHighlights();
            });
        } else {
            el.addEventListener("click", function (e) {
                if (e.target.tagName === "INPUT") return;
                e.preventDefault();
                toggleIngredient(idx);
            });
        }
    });

    stepEls.forEach(function (el) {
        var idx = parseInt(el.dataset.stepIdx, 10);
        if (!stepToIngredients[idx] || !stepToIngredients[idx].length) return;

        el.classList.add("linkable");

        if (hasHover) {
            el.addEventListener("mouseenter", function () {
                highlightStep(idx);
            });
            el.addEventListener("mouseleave", function () {
                clearHighlights();
            });
        } else {
            el.addEventListener("click", function (e) {
                if (e.target.tagName === "INPUT") return;
                e.preventDefault();
                toggleStep(idx);
            });
        }
    });

    var activeIngredient = -1;
    var activeStep = -1;

    function highlightIngredient(idx) {
        ingredientEls[idx].classList.add("linked-highlight");
        ingredientToSteps[idx].forEach(function (stepIdx) {
            stepEls[stepIdx].classList.add("linked-highlight");
        });
    }

    function highlightStep(idx) {
        stepEls[idx].classList.add("linked-highlight");
        stepToIngredients[idx].forEach(function (ingIdx) {
            ingredientEls[ingIdx].classList.add("linked-highlight");
        });
    }

    function clearHighlights() {
        document.querySelectorAll(".linked-highlight").forEach(function (el) {
            el.classList.remove("linked-highlight");
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
})();
