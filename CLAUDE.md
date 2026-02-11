# Just Show Me the Recipe!

## Project overview
Web app that extracts recipes from URLs, stripping away blog content and ads. Built with FastAPI + Jinja2 templates, server-side rendered.

## Architecture
- `app/main.py` — FastAPI app, routes (`GET /`, `POST /parse`)
- `app/models.py` — Pydantic `Recipe` model, `ParseError` exception
- `app/parser/pipeline.py` — Orchestrator: fetch URL → try Tier 1 → Tier 2 → error
- `app/parser/structured.py` — Tier 1: Schema.org extraction via `extruct`
- `app/parser/scrapers.py` — Tier 2: `recipe-scrapers` library fallback
- `app/templates/` — Jinja2 templates (base, index, recipe, error)
- `app/static/` — CSS + JS (minimal, no build step)

## Commands
- Run: `python -m uvicorn app.main:app --reload`
- Test: `pytest tests/`
- Activate venv: `source venv_recipe/bin/activate`

## Current status
- Phase 1 (MVP) complete: URL input → fetch & parse → display recipe
- Phase 2 planned: ingredient parsing (NLP), serving size scaling, ingredient-to-step linking
