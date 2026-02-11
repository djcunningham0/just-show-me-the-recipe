"""Tier 1: Extract recipe from Schema.org structured data via extruct."""

import logging

import extruct

from app.models import Recipe

logger = logging.getLogger(__name__)


def extract_from_html(html: str, url: str) -> Recipe | None:
    """Try to extract a Recipe from structured data in HTML."""
    data = extruct.extract(html, base_url=url, syntaxes=["json-ld", "microdata"])

    recipe_obj = _find_recipe_objects(data.get("json-ld", []))
    source = "json-ld"
    if recipe_obj is None:
        recipe_obj = _find_recipe_objects(data.get("microdata", []))
        source = "microdata"
    if recipe_obj is None:
        logger.debug("No structured recipe data found")
        return None

    logger.debug("Found recipe via %s", source)

    ingredients = recipe_obj.get("recipeIngredient", [])
    steps = _normalize_instructions(recipe_obj.get("recipeInstructions", []))

    if not ingredients and not steps:
        logger.debug("Structured data had no ingredients or steps")
        return None

    # Handle image field (can be string, list, or dict)
    image = recipe_obj.get("image")
    if isinstance(image, list):
        image = image[0] if image else None
    if isinstance(image, dict):
        image = image.get("url")

    # Handle yield/servings
    servings = recipe_obj.get("recipeYield")
    if isinstance(servings, list):
        servings = servings[0] if servings else None
    if servings is not None:
        servings = str(servings)

    return Recipe(
        title=recipe_obj.get("name", "Untitled Recipe"),
        source_url=url,
        servings=servings,
        prep_time=_normalize_time(recipe_obj.get("prepTime")),
        cook_time=_normalize_time(recipe_obj.get("cookTime")),
        image_url=image,
        ingredients=ingredients,
        steps=steps,
    )


def _find_recipe_objects(data: list[dict]) -> dict | None:
    """Find a Recipe object in a list of JSON-LD or microdata items."""
    for item in data:
        # Direct Recipe type
        item_type = item.get("@type", "")
        if isinstance(item_type, list):
            item_type = " ".join(item_type)
        if "Recipe" in item_type:
            return item

        # Check inside @graph arrays
        graph = item.get("@graph", [])
        for node in graph:
            node_type = node.get("@type", "")
            if isinstance(node_type, list):
                node_type = " ".join(node_type)
            if "Recipe" in node_type:
                return node

    return None


def _normalize_instructions(raw) -> list[str]:
    """Normalize recipeInstructions into a flat list of step strings."""
    if isinstance(raw, str):
        # Single text block — split on newlines
        return [s.strip() for s in raw.split("\n") if s.strip()]

    if isinstance(raw, list):
        steps = []
        for item in raw:
            if isinstance(item, str):
                steps.append(item.strip())
            elif isinstance(item, dict):
                # HowToStep or HowToSection
                if item.get("@type") == "HowToSection":
                    section_steps = item.get("itemListElement", [])
                    for sub in section_steps:
                        if isinstance(sub, dict):
                            steps.append(sub.get("text", "").strip())
                        elif isinstance(sub, str):
                            steps.append(sub.strip())
                else:
                    steps.append(item.get("text", "").strip())
        return [s for s in steps if s]

    return []


def _normalize_time(val) -> str | None:
    """Convert ISO 8601 duration to human-readable string."""
    if not val or not isinstance(val, str):
        return None
    # Strip "PT" prefix and convert
    s = val.upper().replace("PT", "").replace("P", "")
    parts = []
    if "H" in s:
        hours, s = s.split("H", 1)
        parts.append(f"{int(hours)}h")
    if "M" in s:
        minutes, s = s.split("M", 1)
        parts.append(f"{int(minutes)}m")
    return " ".join(parts) if parts else val
