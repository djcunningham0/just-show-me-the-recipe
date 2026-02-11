"""FastAPI application for Just Show Me the Recipe."""

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.models import ParseError
from app.parser.pipeline import parse_recipe

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="Just Show Me the Recipe!")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/recipe", response_class=HTMLResponse)
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
