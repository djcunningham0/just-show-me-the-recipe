"""Ingredient string parsing using ingredient-parser-nlp."""

import logging
from fractions import Fraction

from ingredient_parser import parse_ingredient

from app.models import ParsedIngredient, Recipe

logger = logging.getLogger(__name__)


def enrich_recipe(recipe: Recipe) -> Recipe:
    """Parse raw ingredient strings into structured data."""
    recipe.parsed_ingredients = [_parse_single(raw) for raw in recipe.ingredients]
    return recipe


def _parse_single(raw: str) -> ParsedIngredient:
    """Parse a single ingredient string, falling back to raw on failure."""
    try:
        result = parse_ingredient(raw)
        return ParsedIngredient(
            raw=raw,
            amount=_extract_amount(result),
            amount_max=_extract_amount_max(result),
            unit=_extract_unit(result),
            name=_extract_name(result),
            preparation=_extract_text(result.preparation),
            comment=_extract_text(result.comment),
        )
    except Exception:
        logger.debug("Failed to parse ingredient: %s", raw)
        return ParsedIngredient(raw=raw, name=raw)


def _extract_amount(result) -> float | None:
    """Extract primary quantity as float."""
    if not result.amount:
        return None
    return _fraction_to_float(result.amount[0].quantity)


def _extract_amount_max(result) -> float | None:
    """Extract max quantity for ranges (e.g., '2-3 cloves')."""
    if not result.amount:
        return None
    amt = result.amount[0]
    if not amt.RANGE:
        return None
    return _fraction_to_float(amt.quantity_max)


def _extract_unit(result) -> str | None:
    """Extract unit as a plain string."""
    if not result.amount:
        return None
    unit = result.amount[0].unit
    if not unit or unit == "":
        return None
    return str(unit)


def _extract_name(result) -> str:
    """Join ingredient name parts (handles 'salt and pepper')."""
    if not result.name:
        return ""
    return " and ".join(part.text for part in result.name)


def _extract_text(field) -> str | None:
    """Extract text from an optional IngredientText field."""
    if field is None:
        return None
    return field.text


def _fraction_to_float(value: Fraction | int | float) -> float:
    return float(value)
