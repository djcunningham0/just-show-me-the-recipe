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

    var AMBIGUOUS_COMPOUNDS = {
        "pepper": ["bell", "cayenne", "chili", "chile", "jalape"],
        "cream": ["ice"],
        "sauce": ["hot"],
        "oil": ["essential"],
    };

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

        var allVariants = [];
        for (var i = 0; i < candidates.length; i++) {
            var pv = pluralVariants(candidates[i]);
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
            var baseWord = word.replace(/e?s$/, "");
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

    var activeIngredient = -1;
    var activeStep = -1;
    // Store bound handlers so we can remove them on deactivate
    var boundHandlers = [];

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
