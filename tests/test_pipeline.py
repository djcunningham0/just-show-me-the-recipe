"""Tests for the recipe parsing pipeline."""

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.models import ParseError, Recipe
from app.parser.pipeline import parse_recipe
from app.parser.structured import (
    _normalize_instructions,
    _normalize_time,
    extract_from_html,
)
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

JSONLD_IMAGE_LIST_HTML = """
<html><head>
<script type="application/ld+json">
{
    "@context": "https://schema.org",
    "@type": "Recipe",
    "name": "Image List Recipe",
    "recipeIngredient": ["a", "b"],
    "recipeInstructions": [{"@type": "HowToStep", "text": "Do it."}],
    "image": ["https://example.com/first.jpg", "https://example.com/second.jpg"]
}
</script>
</head><body></body></html>
"""

JSONLD_IMAGE_OBJECT_HTML = """
<html><head>
<script type="application/ld+json">
{
    "@context": "https://schema.org",
    "@type": "Recipe",
    "name": "Image Object Recipe",
    "recipeIngredient": ["a"],
    "recipeInstructions": [{"@type": "HowToStep", "text": "Do it."}],
    "image": {"@type": "ImageObject", "url": "https://example.com/photo.jpg"}
}
</script>
</head><body></body></html>
"""

JSONLD_LIST_TYPE_HTML = """
<html><head>
<script type="application/ld+json">
{
    "@context": "https://schema.org",
    "@type": ["Recipe", "HowTo"],
    "name": "Multi-Type Recipe",
    "recipeIngredient": ["flour"],
    "recipeInstructions": [{"@type": "HowToStep", "text": "Mix."}]
}
</script>
</head><body></body></html>
"""

JSONLD_EMPTY_INGREDIENTS_HTML = """
<html><head>
<script type="application/ld+json">
{
    "@context": "https://schema.org",
    "@type": "Recipe",
    "name": "Empty Recipe",
    "recipeIngredient": [],
    "recipeInstructions": []
}
</script>
</head><body></body></html>
"""

JSONLD_YIELD_LIST_HTML = """
<html><head>
<script type="application/ld+json">
{
    "@context": "https://schema.org",
    "@type": "Recipe",
    "name": "Yield List",
    "recipeIngredient": ["flour"],
    "recipeInstructions": [{"@type": "HowToStep", "text": "Mix."}],
    "recipeYield": ["4 servings", "4"]
}
</script>
</head><body></body></html>
"""

# HTML that has no structured data but has heuristic-parseable content
HEURISTIC_FALLBACK_HTML = """
<html><body>
<h1>Grandma's Soup</h1>
<h2>Ingredients</h2>
<ul><li>water</li><li>salt</li></ul>
<h2>Directions</h2>
<ol><li>Boil water.</li><li>Add salt.</li></ol>
</body></html>
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
    recipe = extract_from_html(
        JSONLD_STRING_INSTRUCTIONS_HTML, "https://example.com/toast"
    )
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
    result = extract_with_scraper(
        "https://example.com", "<html><body>Nothing</body></html>"
    )
    assert result is None


# -- Tests: error model --


def test_parse_error():
    err = ParseError("network", "Timed out")
    assert err.error_type == "network"
    assert err.message == "Timed out"
    assert str(err) == "Timed out"


# -- Tests: structured data edge cases --


def test_image_as_list():
    recipe = extract_from_html(JSONLD_IMAGE_LIST_HTML, "https://example.com")
    assert recipe is not None
    assert recipe.image_url == "https://example.com/first.jpg"


def test_image_as_object():
    recipe = extract_from_html(JSONLD_IMAGE_OBJECT_HTML, "https://example.com")
    assert recipe is not None
    assert recipe.image_url == "https://example.com/photo.jpg"


def test_list_type():
    """@type can be a list like ['Recipe', 'HowTo']."""
    recipe = extract_from_html(JSONLD_LIST_TYPE_HTML, "https://example.com")
    assert recipe is not None
    assert recipe.title == "Multi-Type Recipe"


def test_empty_ingredients_and_steps_returns_none():
    recipe = extract_from_html(JSONLD_EMPTY_INGREDIENTS_HTML, "https://example.com")
    assert recipe is None


def test_yield_as_list():
    recipe = extract_from_html(JSONLD_YIELD_LIST_HTML, "https://example.com")
    assert recipe is not None
    assert recipe.servings == "4 servings"


# -- Tests: _normalize_time --


def test_normalize_time_minutes():
    assert _normalize_time("PT30M") == "30m"


def test_normalize_time_hours_and_minutes():
    assert _normalize_time("PT1H30M") == "1h 30m"


def test_normalize_time_hours_only():
    assert _normalize_time("PT2H") == "2h"


def test_normalize_time_none():
    assert _normalize_time(None) is None


def test_normalize_time_non_string():
    assert _normalize_time(30) is None


# -- Tests: pipeline orchestration (mocked HTTP) --


def _make_mock_response(html: str, status_code: int = 200) -> httpx.Response:
    """Create a mock httpx.Response with the given HTML content."""
    return httpx.Response(status_code=status_code, text=html, request=httpx.Request("GET", "https://example.com"))


@pytest.mark.anyio
@patch("app.parser.pipeline.httpx.AsyncClient")
async def test_pipeline_tier1_success(mock_client_cls):
    """parse_recipe returns Tier 1 result when structured data exists."""
    mock_client = AsyncMock()
    mock_client.get.return_value = _make_mock_response(JSONLD_RECIPE_HTML)
    mock_client_cls.return_value.__aenter__.return_value = mock_client

    recipe = await parse_recipe("https://example.com/cookies")
    assert recipe.title == "Test Cookies"
    assert len(recipe.ingredients) == 3


@pytest.mark.anyio
@patch("app.parser.pipeline.httpx.AsyncClient")
async def test_pipeline_falls_through_to_heuristic(mock_client_cls):
    """parse_recipe falls through to Tier 3 when Tier 1 and 2 fail."""
    mock_client = AsyncMock()
    mock_client.get.return_value = _make_mock_response(HEURISTIC_FALLBACK_HTML)
    mock_client_cls.return_value.__aenter__.return_value = mock_client

    recipe = await parse_recipe("https://example.com/blog-recipe")
    assert recipe.title == "Grandma's Soup"
    assert "water" in recipe.ingredients


@pytest.mark.anyio
@patch("app.parser.pipeline.httpx.AsyncClient")
async def test_pipeline_no_recipe_raises(mock_client_cls):
    """parse_recipe raises ParseError when no tier finds a recipe."""
    mock_client = AsyncMock()
    mock_client.get.return_value = _make_mock_response(NO_RECIPE_HTML)
    mock_client_cls.return_value.__aenter__.return_value = mock_client

    with pytest.raises(ParseError, match="No recipe found"):
        await parse_recipe("https://example.com/blog")


@pytest.mark.anyio
@patch("app.parser.pipeline.httpx.AsyncClient")
async def test_pipeline_timeout(mock_client_cls):
    """parse_recipe raises ParseError on timeout."""
    mock_client = AsyncMock()
    mock_client.get.side_effect = httpx.TimeoutException("timed out")
    mock_client_cls.return_value.__aenter__.return_value = mock_client

    with pytest.raises(ParseError, match="timed out"):
        await parse_recipe("https://example.com/slow")


@pytest.mark.anyio
@patch("app.parser.pipeline.httpx.AsyncClient")
async def test_pipeline_http_error(mock_client_cls):
    """parse_recipe raises ParseError on HTTP error status."""
    mock_client = AsyncMock()
    resp = _make_mock_response("", status_code=403)
    mock_client.get.return_value = resp
    mock_client_cls.return_value.__aenter__.return_value = mock_client

    with pytest.raises(ParseError, match="403"):
        await parse_recipe("https://example.com/blocked")
