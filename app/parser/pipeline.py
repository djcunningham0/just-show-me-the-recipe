"""Orchestrator: fetch URL and run parsing tiers."""

import ipaddress
import socket
from urllib.parse import urlparse

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
        raise ParseError("validation", "Only http and https URLs are supported.")

    hostname = parsed.hostname
    if not hostname:
        raise ParseError("validation", "Invalid URL.")

    try:
        addrinfos = socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        raise ParseError("network", "Could not resolve hostname.")

    for _, _, _, _, sockaddr in addrinfos:
        ip = ipaddress.ip_address(sockaddr[0])
        for network in _BLOCKED_NETWORKS:
            if ip in network:
                raise ParseError(
                    "validation",
                    "Requests to private or internal addresses are not allowed.",
                )


async def parse_recipe(url: str) -> Recipe:
    """Fetch a URL and extract a recipe from it."""
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
