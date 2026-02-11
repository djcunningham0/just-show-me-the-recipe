"""Tier 3: Heuristic extraction from unstructured HTML."""

import logging
import re

from bs4 import BeautifulSoup

from app.models import Recipe

logger = logging.getLogger(__name__)

_INGREDIENT_RE = re.compile(r"ingredients\s*:?", re.IGNORECASE)
_INSTRUCTION_RE = re.compile(
    r"(?:instructions|directions|steps|method)\s*:?", re.IGNORECASE
)
_HEADING_TAGS = ["h1", "h2", "h3", "h4", "h5", "h6"]
_LABEL_TAGS = [*_HEADING_TAGS, "strong", "b"]


def extract_heuristic(html: str, url: str) -> Recipe | None:
    """Try to extract a recipe by finding ingredient/instruction patterns in HTML."""
    soup = BeautifulSoup(html, "html.parser")

    ingredients = _find_list_after_label(soup, _INGREDIENT_RE)
    steps = _find_list_after_label(soup, _INSTRUCTION_RE)

    logger.debug(
        "Heuristic found %d ingredients, %d steps", len(ingredients), len(steps)
    )

    if not ingredients and not steps:
        return None

    title = _extract_title(soup)

    return Recipe(
        title=title,
        source_url=url,
        ingredients=ingredients,
        steps=steps,
    )


def _find_list_after_label(soup: BeautifulSoup, pattern: re.Pattern) -> list[str]:
    """Find a <ul>/<ol> that follows a label matching the pattern."""
    for tag in soup.find_all(_LABEL_TAGS):
        if not pattern.search(tag.get_text(strip=True)):
            continue

        # The label might be inside a <p> wrapper — look from the parent
        search_from = tag.parent if tag.parent.name == "p" else tag
        ul = search_from.find_next(["ul", "ol"])
        if ul:
            items = [li.get_text(strip=True) for li in ul.find_all("li")]
            if items:
                return items

    return []


def _extract_title(soup: BeautifulSoup) -> str:
    """
    Extract a recipe title from the page, falling back through og:title, <title> (with
    site name suffix stripped), and <h1>.
    """
    og = soup.find("meta", property="og:title")
    if og and og.get("content", "").strip():
        return og["content"].strip()

    title_tag = soup.find("title")
    if title_tag:
        text = title_tag.get_text(strip=True)
        # Strip common suffixes like " — Site Name" or " | Site Name"
        text = re.split(r"\s*[—|–\-]\s*(?!.*[—|–\-])", text)[0].strip()
        if text:
            return text

    h1 = soup.find("h1")
    if h1:
        return h1.get_text(strip=True)

    return "Untitled Recipe"
