"""Orchestrator: fetch URL and run parsing tiers."""

import ipaddress
import logging
import socket
from urllib.parse import urlparse

import httpx
from cachetools import TTLCache

from app.models import ParseError, Recipe
from app.parser.heuristic import extract_heuristic
from app.parser.ingredients import enrich_recipe
from app.parser.scrapers import extract_with_scraper
from app.parser.structured import extract_from_html

logger = logging.getLogger(__name__)

# In-memory cache: up to 128 recipes, 30-minute TTL
_recipe_cache: TTLCache[str, Recipe] = TTLCache(maxsize=128, ttl=30 * 60)

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


_BLOCKED_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
]


def validate_url(url: str) -> None:
    """Validate URL scheme and block requests to private/reserved IPs."""
    parsed = urlparse(url)

    if parsed.scheme not in ("http", "https"):
        logger.warning("Rejected URL with scheme %r: %s", parsed.scheme, url)
        raise ParseError("validation", "Only http and https URLs are supported.")

    hostname = parsed.hostname
    if not hostname:
        logger.warning("Rejected URL with no hostname: %s", url)
        raise ParseError("validation", "Invalid URL.")

    try:
        addrinfos = socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        logger.warning("DNS resolution failed for %s", hostname)
        raise ParseError(
            "network", "Couldn't find that website. Check the URL for typos."
        )

    for _, _, _, _, sockaddr in addrinfos:
        ip = ipaddress.ip_address(sockaddr[0])
        for network in _BLOCKED_NETWORKS:
            if ip in network:
                logger.warning("Blocked private IP %s for hostname %s", ip, hostname)
                raise ParseError(
                    "validation",
                    "Requests to private or internal addresses are not allowed.",
                )


async def parse_recipe(url: str) -> Recipe:
    """Fetch a URL and extract a recipe from it."""
    cached = _recipe_cache.get(url)
    if cached is not None:
        logger.info("Cache hit for %s", url)
        return cached

    logger.info("Parsing recipe from %s", url)
    validate_url(url)
    try:
        async with httpx.AsyncClient(
            timeout=10.0,
            follow_redirects=True,
            headers={"User-Agent": USER_AGENT},
        ) as client:
            response = await client.get(url)
            response.raise_for_status()
    except httpx.TimeoutException:
        logger.warning("Timeout fetching %s", url)
        raise ParseError("network", "Request timed out. The site may be slow or down.")
    except httpx.ConnectError:
        logger.warning("Connection error fetching %s", url)
        raise ParseError(
            "network",
            "Couldn't connect to the site. It may be down or the URL may be wrong.",
        )
    except httpx.HTTPStatusError as e:
        status = e.response.status_code
        logger.warning("HTTP %d from %s", status, url)
        if status in (401, 403):
            msg = "This site blocked the request. It may require a login or restrict automated access."
        elif status == 404:
            msg = "Page not found. Double-check the URL and make sure it points to a recipe page."
        elif status >= 500:
            msg = "The recipe site is having server issues. Try again in a few minutes."
        else:
            msg = f"The site returned an error (HTTP {status})."
        raise ParseError("http", msg)
    except httpx.RequestError as e:
        logger.warning("Request error fetching %s: %s", url, e)
        raise ParseError(
            "network",
            "Something went wrong fetching that page. Check the URL and try again.",
        )

    logger.info(
        "Fetched %s (HTTP %d, %d bytes)", url, response.status_code, len(response.text)
    )
    html = response.text

    # Try extraction tiers in order
    tiers = [
        ("Tier 1 (structured data)", lambda: extract_from_html(html, url)),
        ("Tier 2 (recipe-scrapers)", lambda: extract_with_scraper(url, html)),
        ("Tier 3 (heuristic)", lambda: extract_heuristic(html, url)),
    ]

    recipe = None
    for name, extract in tiers:
        recipe = extract()
        if recipe is not None:
            logger.info("%s succeeded for %s", name, url)
            break
        logger.debug("%s found nothing for %s", name, url)

    if recipe is None:
        logger.warning("All tiers failed for %s", url)
        raise ParseError("parse", "No recipe found on that page. Try a different URL.")

    enrich_recipe(recipe)
    _recipe_cache[url] = recipe
    return recipe
