"""Tests for ingredient string parsing."""


from app.models import ParsedIngredient, Recipe
from app.parser.ingredients import _parse_single, enrich_recipe

# -- _parse_single tests --


def test_parse_simple_ingredient():
    result = _parse_single("2 cups all-purpose flour")
    assert result.amount == 2.0
    assert result.unit == "cup"
    assert "flour" in result.name
    assert result.raw == "2 cups all-purpose flour"


def test_parse_fraction():
    result = _parse_single("1/2 tsp salt")
    assert result.amount == 0.5
    assert "salt" in result.name


def test_parse_unitless():
    result = _parse_single("3 large eggs")
    assert result.amount == 3.0
    assert result.unit is None
    assert "egg" in result.name


def test_parse_no_amount():
    result = _parse_single("salt and pepper to taste")
    assert result.amount is None
    assert result.comment is not None
    assert "taste" in result.comment


def test_parse_range():
    result = _parse_single("2-3 cloves garlic")
    assert result.amount == 2.0
    assert result.amount_max == 3.0


def test_parse_preparation():
    result = _parse_single("1 onion, diced")
    assert result.preparation is not None
    assert "dice" in result.preparation.lower()


def test_parse_fallback_on_empty_string():
    result = _parse_single("")
    assert result.raw == ""
    assert isinstance(result, ParsedIngredient)


def test_parse_preserves_raw():
    raw = "1 (14 oz) can diced tomatoes"
    result = _parse_single(raw)
    assert result.raw == raw
    assert result.amount is not None
    assert result.name != ""


# -- enrich_recipe tests --


def test_enrich_recipe_populates_parsed_ingredients():
    recipe = Recipe(
        title="Test",
        source_url="https://example.com",
        ingredients=["2 cups flour", "1 tsp salt", "3 eggs"],
        steps=["Mix together."],
    )
    enrich_recipe(recipe)
    assert recipe.parsed_ingredients is not None
    assert len(recipe.parsed_ingredients) == 3
    assert recipe.parsed_ingredients[0].amount == 2.0
    assert recipe.parsed_ingredients[2].amount == 3.0


def test_enrich_recipe_with_empty_ingredients():
    recipe = Recipe(
        title="Test",
        source_url="https://example.com",
        ingredients=[],
        steps=["Do nothing."],
    )
    enrich_recipe(recipe)
    assert recipe.parsed_ingredients == []


def test_enrich_recipe_graceful_fallback():
    """Unparseable ingredients should not crash enrichment."""
    recipe = Recipe(
        title="Test",
        source_url="https://example.com",
        ingredients=["2 cups flour", "a generous handful of love"],
        steps=["Mix."],
    )
    enrich_recipe(recipe)
    assert recipe.parsed_ingredients is not None
    assert len(recipe.parsed_ingredients) == 2
    # Both should have raw preserved
    assert recipe.parsed_ingredients[0].raw == "2 cups flour"
    assert recipe.parsed_ingredients[1].raw == "a generous handful of love"
