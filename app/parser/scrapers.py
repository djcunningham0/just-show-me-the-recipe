"""Tier 2: Extract recipe using the recipe-scrapers library."""

from recipe_scrapers import scrape_html

from app.models import Recipe


def extract_with_scraper(url: str, html: str) -> Recipe | None:
    """Try to extract a Recipe using recipe-scrapers."""
    try:
        scraper = scrape_html(html, org_url=url)
    except Exception:
        return None

    try:
        ingredients = scraper.ingredients()
    except Exception:
        ingredients = []

    try:
        instructions = scraper.instructions()
    except Exception:
        instructions = ""

    steps = [s.strip() for s in instructions.split("\n") if s.strip()]

    if not ingredients and not steps:
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
