"""Orchestrator: fetch URL and run parsing tiers."""

import ipaddress
import logging
import socket
from urllib.parse import urlparse

import httpx
from cachetools import TTLCache

from app.models import ParseError, Recipe
from app.parser.heuristic import extract_heuristic
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
        raise ParseError("network", "Could not resolve hostname.")

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
        raise ParseError("network", "Could not connect to the site. Check the URL.")
    except httpx.HTTPStatusError as e:
        logger.warning("HTTP %d from %s", e.response.status_code, url)
        raise ParseError(
            "http", f"Site returned an error (HTTP {e.response.status_code})."
        )
    except httpx.RequestError as e:
        logger.warning("Request error fetching %s: %s", url, e)
        raise ParseError(
            "network", "Could not fetch the URL. Check the URL and try again."
        )

    logger.info("Fetched %s (HTTP %d, %d bytes)", url, response.status_code, len(response.text))
    html = response.text

    # Tier 1: structured data
    recipe = extract_from_html(html, url)
    if recipe is not None:
        logger.info("Tier 1 (structured data) succeeded for %s", url)
        _recipe_cache[url] = recipe
        return recipe
    logger.debug("Tier 1 (structured data) found nothing for %s", url)

    # Tier 2: recipe-scrapers
    recipe = extract_with_scraper(url, html)
    if recipe is not None:
        logger.info("Tier 2 (recipe-scrapers) succeeded for %s", url)
        _recipe_cache[url] = recipe
        return recipe
    logger.debug("Tier 2 (recipe-scrapers) found nothing for %s", url)

    # Tier 3: heuristic HTML parsing
    recipe = extract_heuristic(html, url)
    if recipe is not None:
        logger.info("Tier 3 (heuristic) succeeded for %s", url)
        _recipe_cache[url] = recipe
        return recipe
    logger.debug("Tier 3 (heuristic) found nothing for %s", url)

    logger.warning("All tiers failed for %s", url)
    raise ParseError("parse", "No recipe found on that page. Try a different URL.")
