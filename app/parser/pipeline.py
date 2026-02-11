"""Orchestrator: fetch URL and run parsing tiers."""

import httpx

from app.models import ParseError, Recipe
from app.parser.heuristic import extract_heuristic
from app.parser.scrapers import extract_with_scraper
from app.parser.structured import extract_from_html

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


async def parse_recipe(url: str) -> Recipe:
    """Fetch a URL and extract a recipe from it."""
    try:
        async with httpx.AsyncClient(
            timeout=10.0,
            follow_redirects=True,
            headers={"User-Agent": USER_AGENT},
        ) as client:
            response = await client.get(url)
            response.raise_for_status()
    except httpx.TimeoutException:
        raise ParseError("network", "Request timed out. The site may be slow or down.")
    except httpx.ConnectError:
        raise ParseError("network", "Could not connect to the site. Check the URL.")
    except httpx.HTTPStatusError as e:
        raise ParseError(
            "http", f"Site returned an error (HTTP {e.response.status_code})."
        )
    except httpx.RequestError:
        raise ParseError(
            "network", "Could not fetch the URL. Check the URL and try again."
        )

    html = response.text

    # Tier 1: structured data
    recipe = extract_from_html(html, url)
    if recipe is not None:
        return recipe

    # Tier 2: recipe-scrapers
    recipe = extract_with_scraper(url, html)
    if recipe is not None:
        return recipe

    # Tier 3: heuristic HTML parsing
    recipe = extract_heuristic(html, url)
    if recipe is not None:
        return recipe

    raise ParseError("parse", "No recipe found on that page. Try a different URL.")
