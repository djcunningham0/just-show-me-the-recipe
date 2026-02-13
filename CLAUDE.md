# Just Show Me the Recipe!

## Project overview

Web app that extracts recipes from URLs, stripping away blog content and ads. Built with FastAPI + Jinja2 templates, server-side rendered.

## Architecture

- `app/main.py` — FastAPI app, routes (`GET /`, `GET /recipe?url=...`), rate limiting (`slowapi`), security headers middleware
- `app/models.py` — Pydantic `Recipe` model, `ParseError` exception
- `app/parser/pipeline.py` — Orchestrator: validate URL → fetch → try Tier 1 → Tier 2 → Tier 3 → error. Includes SSRF protection (scheme + private IP blocking).
- `app/parser/structured.py` — Tier 1: Schema.org extraction via `extruct`
- `app/parser/scrapers.py` — Tier 2: `recipe-scrapers` library fallback
- `app/parser/heuristic.py` — Tier 3: pattern-matching fallback (looks for ingredients/instructions labels + lists)
- `app/templates/` — Jinja2 templates (base, index, recipe, error)
- `app/parser/ingredients.py` — Ingredient parsing (NLP): extracts ingredient names for highlighting
- `app/static/` — CSS + JS (dark mode, two-column layout, interactive checklists, recently viewed recipes, screen wake lock, recipe scaling, ingredient-to-step highlighting)
- `app/static/recipe-scaler.js` — Client-side recipe scaling (0.5x–3x)
- `app/static/recipe-linker.js` — Ingredient-to-step highlighting with fuzzy matching

## Deployment

- Hosted on Render (free tier), deployed via Docker
- `Dockerfile` — Python 3.13-slim, installs from `pyproject.toml`, runs uvicorn on port 10000
- `render.yaml` — Render blueprint config (free plan, Docker runtime)
- `.dockerignore` — excludes venv, caches, IDE files, `.git` from image

## Commands

- Run: `python -m uvicorn app.main:app --reload`
- Test: `pytest tests/`
- Activate venv: `source venv_recipe/bin/activate`
