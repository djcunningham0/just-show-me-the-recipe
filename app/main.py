"""FastAPI application for Just Show Me the Recipe."""

import logging
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.middleware.base import BaseHTTPMiddleware

from app.models import ParseError
from app.parser.pipeline import parse_recipe

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent

limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="Just Show Me the Recipe!")
app.state.limiter = limiter
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return templates.TemplateResponse(
        request,
        "error.html",
        {
            "error_message": (
                "You're sending too many requests. Please wait a moment and try again."
            )
        },
        status_code=429,
    )


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response


app.add_middleware(SecurityHeadersMiddleware)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(request, "index.html")


@app.get("/recipe", response_class=HTMLResponse)
@limiter.limit("30/minute")
async def recipe(request: Request, url: str = ""):
    if not url.strip():
        return templates.TemplateResponse(
            request,
            "error.html",
            {"error_message": "Please enter a URL to extract a recipe from."},
            status_code=400,
        )
    try:
        result = await parse_recipe(url)
    except ParseError as e:
        logger.warning("ParseError [%s] for %s: %s", e.error_type, url, e.message)
        return templates.TemplateResponse(
            request, "error.html", {"error_message": e.message}
        )
    logger.info("Served recipe %r from %s", result.title, url)
    return templates.TemplateResponse(request, "recipe.html", {"recipe": result})
