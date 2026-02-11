"""Tests for the heuristic (Tier 3) parser."""

from app.parser.heuristic import extract_heuristic


HEURISTIC_FULL_HTML = """
<html>
<head><title>Best Pancakes — My Food Blog</title></head>
<body>
<h1>Best Pancakes Ever</h1>
<p>Long story about my grandma...</p>
<h2>Ingredients</h2>
<ul>
    <li>1 cup flour</li>
    <li>1 egg</li>
    <li>1 cup milk</li>
</ul>
<h2>Directions</h2>
<ol>
    <li>Mix dry ingredients.</li>
    <li>Add wet ingredients and stir.</li>
    <li>Cook on griddle.</li>
</ol>
</body></html>
"""

HEURISTIC_INGREDIENTS_ONLY_HTML = """
<html><body>
<h3>Ingredients:</h3>
<ul><li>salt</li><li>pepper</li></ul>
</body></html>
"""

HEURISTIC_STEPS_ONLY_HTML = """
<html><body>
<h3>Instructions</h3>
<ol><li>Do the thing.</li></ol>
</body></html>
"""

HEURISTIC_NO_RECIPE_HTML = """
<html><body>
<h2>About Us</h2>
<p>We are a tech blog.</p>
</body></html>
"""

HEURISTIC_LABEL_IN_P_HTML = """
<html><body>
<p><strong>Ingredients:</strong></p>
<ul><li>flour</li><li>water</li></ul>
</body></html>
"""

HEURISTIC_METHOD_LABEL_HTML = """
<html><body>
<h2>Method</h2>
<ol><li>Preheat oven.</li><li>Bake.</li></ol>
</body></html>
"""

HEURISTIC_OG_TITLE_HTML = """
<html>
<head><meta property="og:title" content="OG Pancakes" /></head>
<body>
<h2>Ingredients</h2>
<ul><li>flour</li></ul>
</body></html>
"""

HEURISTIC_H1_TITLE_HTML = """
<html><body>
<h1>My Great Recipe</h1>
<h2>Ingredients</h2>
<ul><li>butter</li></ul>
</body></html>
"""

HEURISTIC_NO_TITLE_HTML = """
<html><body>
<h2>Ingredients</h2>
<ul><li>butter</li></ul>
</body></html>
"""

URL = "https://example.com/recipe"


# -- Extraction tests --


def test_full_recipe():
    recipe = extract_heuristic(HEURISTIC_FULL_HTML, URL)
    assert recipe is not None
    assert recipe.ingredients == ["1 cup flour", "1 egg", "1 cup milk"]
    assert recipe.steps == [
        "Mix dry ingredients.",
        "Add wet ingredients and stir.",
        "Cook on griddle.",
    ]


def test_ingredients_only():
    recipe = extract_heuristic(HEURISTIC_INGREDIENTS_ONLY_HTML, URL)
    assert recipe is not None
    assert recipe.ingredients == ["salt", "pepper"]
    assert recipe.steps == []


def test_steps_only():
    recipe = extract_heuristic(HEURISTIC_STEPS_ONLY_HTML, URL)
    assert recipe is not None
    assert recipe.steps == ["Do the thing."]
    assert recipe.ingredients == []


def test_no_recipe():
    recipe = extract_heuristic(HEURISTIC_NO_RECIPE_HTML, URL)
    assert recipe is None


def test_label_inside_p_wrapper():
    """Labels wrapped in <p><strong>...</strong></p> should still find the list."""
    recipe = extract_heuristic(HEURISTIC_LABEL_IN_P_HTML, URL)
    assert recipe is not None
    assert recipe.ingredients == ["flour", "water"]


def test_method_label():
    """'Method' should be recognized as an instruction label."""
    recipe = extract_heuristic(HEURISTIC_METHOD_LABEL_HTML, URL)
    assert recipe is not None
    assert recipe.steps == ["Preheat oven.", "Bake."]


# -- Title extraction tests --


def test_title_from_og():
    recipe = extract_heuristic(HEURISTIC_OG_TITLE_HTML, URL)
    assert recipe is not None
    assert recipe.title == "OG Pancakes"


def test_title_from_title_tag_strips_suffix():
    recipe = extract_heuristic(HEURISTIC_FULL_HTML, URL)
    assert recipe is not None
    assert recipe.title == "Best Pancakes"


def test_title_from_h1():
    recipe = extract_heuristic(HEURISTIC_H1_TITLE_HTML, URL)
    assert recipe is not None
    assert recipe.title == "My Great Recipe"


def test_title_fallback():
    recipe = extract_heuristic(HEURISTIC_NO_TITLE_HTML, URL)
    assert recipe is not None
    assert recipe.title == "Untitled Recipe"
