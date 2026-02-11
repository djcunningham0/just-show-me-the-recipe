# Just Show Me the Recipe!

Paste a recipe URL, get just the ingredients and steps.
No fluff (unless the recipe calls for it).

## Setup

```bash
python -m venv venv_recipe
source venv_recipe/bin/activate
pip install -r requirements.txt
```

## Run

```bash
python -m uvicorn app.main:app --reload
```

Then open http://localhost:8000.

## How it works

The parser tries two extraction strategies in order:

1. **Schema.org structured data** (JSON-LD / Microdata via `extruct`) — works on most major recipe sites
2. **recipe-scrapers** fallback — covers additional sites with site-specific scrapers

## Tests

```bash
pytest tests/
```
