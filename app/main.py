"""FastAPI application for Just Show Me the Recipe."""

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.middleware.base import BaseHTTPMiddleware

from app.models import ParseError
from app.parser.pipeline import parse_recipe

BASE_DIR = Path(__file__).resolve().parent

limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="Just Show Me the Recipe!")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")


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
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/recipe", response_class=HTMLResponse)
@limiter.limit("30/minute")
async def recipe(request: Request, url: str):
    try:
        recipe = await parse_recipe(url)
    except ParseError as e:
        return templates.TemplateResponse(
            "error.html",
            {"request": request, "error_message": e.message},
        )
    return templates.TemplateResponse(
        "recipe.html",
        {"request": request, "recipe": recipe},
    )
