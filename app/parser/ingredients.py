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
        amt = _find_primary_amount(result)
        return ParsedIngredient(
            raw=raw,
            amount=_extract_amount(amt),
            amount_max=_extract_amount_max(amt),
            unit=_extract_unit(amt),
            name=_extract_name(result),
            preparation=_extract_text(result.preparation),
            comment=_extract_text(result.comment),
        )
    except Exception:
        logger.debug("Failed to parse ingredient: %s", raw)
        return ParsedIngredient(raw=raw, name=raw)


def _find_primary_amount(result):
    """Return the first amount entry that has a real numeric quantity.

    The NLP parser can return multiple entries — e.g. "Heaping 1/3 cup" yields
    one for "Heaping" (empty quantity) and one for "1/3 cup".  We skip entries
    whose quantity is empty or None so the actual number is used for scaling.
    """
    if not result.amount:
        return None
    for amt in result.amount:
        if amt.quantity != "" and amt.quantity is not None:
            return amt
    return None


def _extract_amount(amt) -> float | None:
    """Extract primary quantity as float."""
    if amt is None:
        return None
    return _fraction_to_float(amt.quantity)


def _extract_amount_max(amt) -> float | None:
    """Extract max quantity for ranges (e.g., '2-3 cloves')."""
    if amt is None or not amt.RANGE:
        return None
    return _fraction_to_float(amt.quantity_max)


_UNIT_NORMALIZE = {
    "tbsps": "tbsp",
    "tsps": "tsp",
}


def _extract_unit(amt) -> str | None:
    """Extract unit as a plain string, normalizing common abbreviations."""
    if amt is None:
        return None
    unit = amt.unit
    if not unit or unit == "":
        return None
    unit = str(unit)
    return _UNIT_NORMALIZE.get(unit.lower(), unit)


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
