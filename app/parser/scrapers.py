"""Tier 2: Extract recipe using the recipe-scrapers library."""

import logging

from recipe_scrapers import scrape_html

from app.models import Recipe

logger = logging.getLogger(__name__)


def extract_with_scraper(url: str, html: str) -> Recipe | None:
    """Try to extract a Recipe using recipe-scrapers."""
    try:
        scraper = scrape_html(html, org_url=url, supported_only=False)
    except Exception:
        logger.debug("recipe-scrapers failed to initialize", exc_info=True)
        return None

    try:
        ingredients = scraper.ingredients()
    except Exception:
        logger.debug("recipe-scrapers failed to extract ingredients", exc_info=True)
        ingredients = []

    try:
        instructions = scraper.instructions()
    except Exception:
        logger.debug("recipe-scrapers failed to extract instructions", exc_info=True)
        instructions = ""

    steps = [s.strip() for s in instructions.split("\n") if s.strip()]

    if not ingredients and not steps:
        logger.debug("recipe-scrapers found no ingredients or steps")
        return None

    def _safe_get(method):
        try:
            val = method()
            return val if val else None
        except Exception:
            return None

    title = _safe_get(scraper.title) or "Untitled Recipe"
    servings = _safe_get(scraper.yields)
    image = _safe_get(scraper.image)
    prep_time = _safe_get(scraper.prep_time)
    cook_time = _safe_get(scraper.cook_time)

    return Recipe(
        title=title,
        source_url=url,
        servings=str(servings) if servings else None,
        prep_time=f"{prep_time}m" if isinstance(prep_time, int) else prep_time,
        cook_time=f"{cook_time}m" if isinstance(cook_time, int) else cook_time,
        image_url=image,
        ingredients=ingredients,
        steps=steps,
    )
