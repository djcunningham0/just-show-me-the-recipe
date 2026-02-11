"""Tests for the recipe parsing pipeline."""

import pytest

from app.models import ParseError, Recipe
from app.parser.structured import _normalize_instructions, extract_from_html
from app.parser.scrapers import extract_with_scraper


# -- Fixtures: sample HTML snippets --

JSONLD_RECIPE_HTML = """
<html><head>
<script type="application/ld+json">
{
    "@context": "https://schema.org",
    "@type": "Recipe",
    "name": "Test Cookies",
    "recipeIngredient": ["1 cup flour", "1/2 cup sugar", "2 eggs"],
    "recipeInstructions": [
        {"@type": "HowToStep", "text": "Mix flour and sugar."},
        {"@type": "HowToStep", "text": "Add eggs and stir."},
        {"@type": "HowToStep", "text": "Bake at 350F for 12 minutes."}
    ],
    "prepTime": "PT10M",
    "cookTime": "PT12M",
    "recipeYield": "24 cookies",
    "image": "https://example.com/cookies.jpg"
}
</script>
</head><body></body></html>
"""

JSONLD_GRAPH_HTML = """
<html><head>
<script type="application/ld+json">
{
    "@context": "https://schema.org",
    "@graph": [
        {"@type": "WebPage", "name": "Blog Post"},
        {
            "@type": "Recipe",
            "name": "Graph Soup",
            "recipeIngredient": ["water", "salt"],
            "recipeInstructions": "Boil water.\\nAdd salt."
        }
    ]
}
</script>
</head><body></body></html>
"""

JSONLD_STRING_INSTRUCTIONS_HTML = """
<html><head>
<script type="application/ld+json">
{
    "@context": "https://schema.org",
    "@type": "Recipe",
    "name": "Simple Toast",
    "recipeIngredient": ["bread", "butter"],
    "recipeInstructions": "Toast the bread.\\nSpread butter on top."
}
</script>
</head><body></body></html>
"""

NO_RECIPE_HTML = """
<html><head><title>Just a Blog</title></head>
<body><p>No recipe here.</p></body></html>
"""

HOWTOSECTION_HTML = """
<html><head>
<script type="application/ld+json">
{
    "@context": "https://schema.org",
    "@type": "Recipe",
    "name": "Sectioned Recipe",
    "recipeIngredient": ["flour", "water"],
    "recipeInstructions": [
        {
            "@type": "HowToSection",
            "name": "Prep",
            "itemListElement": [
                {"@type": "HowToStep", "text": "Measure flour."},
                {"@type": "HowToStep", "text": "Boil water."}
            ]
        }
    ]
}
</script>
</head><body></body></html>
"""


# -- Tests: structured data extraction --

def test_extract_jsonld_recipe():
    recipe = extract_from_html(JSONLD_RECIPE_HTML, "https://example.com/cookies")
    assert recipe is not None
    assert recipe.title == "Test Cookies"
    assert len(recipe.ingredients) == 3
    assert len(recipe.steps) == 3
    assert recipe.steps[0] == "Mix flour and sugar."
    assert recipe.prep_time == "10m"
    assert recipe.cook_time == "12m"
    assert recipe.servings == "24 cookies"
    assert recipe.image_url == "https://example.com/cookies.jpg"


def test_extract_jsonld_graph():
    recipe = extract_from_html(JSONLD_GRAPH_HTML, "https://example.com/soup")
    assert recipe is not None
    assert recipe.title == "Graph Soup"
    assert recipe.ingredients == ["water", "salt"]


def test_string_instructions_split():
    recipe = extract_from_html(JSONLD_STRING_INSTRUCTIONS_HTML, "https://example.com/toast")
    assert recipe is not None
    assert len(recipe.steps) == 2
    assert recipe.steps[0] == "Toast the bread."
    assert recipe.steps[1] == "Spread butter on top."


def test_howtosection_extraction():
    recipe = extract_from_html(HOWTOSECTION_HTML, "https://example.com/sectioned")
    assert recipe is not None
    assert len(recipe.steps) == 2
    assert recipe.steps[0] == "Measure flour."


def test_no_recipe_returns_none():
    recipe = extract_from_html(NO_RECIPE_HTML, "https://example.com/blog")
    assert recipe is None


# -- Tests: normalize instructions --

def test_normalize_howto_steps():
    raw = [
        {"@type": "HowToStep", "text": "Step one."},
        {"@type": "HowToStep", "text": "Step two."},
    ]
    assert _normalize_instructions(raw) == ["Step one.", "Step two."]


def test_normalize_string_list():
    raw = ["Do this.", "Do that."]
    assert _normalize_instructions(raw) == ["Do this.", "Do that."]


def test_normalize_single_string():
    raw = "First step.\nSecond step."
    assert _normalize_instructions(raw) == ["First step.", "Second step."]


# -- Tests: recipe-scrapers fallback --

def test_scraper_no_recipe():
    result = extract_with_scraper("https://example.com", "<html><body>Nothing</body></html>")
    assert result is None


# -- Tests: error model --

def test_parse_error():
    err = ParseError("network", "Timed out")
    assert err.error_type == "network"
    assert err.message == "Timed out"
    assert str(err) == "Timed out"
