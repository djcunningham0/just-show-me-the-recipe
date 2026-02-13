# Just Show Me the Recipe!

Paste a recipe URL, get just the ingredients and steps.
No fluff (unless the recipe calls for it).

Currently deployed at https://justshowmetherecipe.onrender.com.

## Setup

```bash
python -m venv venv_recipe
source venv_recipe/bin/activate
pip install .
```

## Run

```bash
python -m uvicorn app.main:app --reload
```

Then open http://localhost:8000.

## How it works

The parser tries three extraction strategies in order:

1. **Schema.org structured data** (JSON-LD / Microdata via `extruct`) — works on most major recipe sites
2. **recipe-scrapers** fallback — covers additional sites with site-specific scrapers
3. **Heuristic** fallback — pattern-matching for ingredients/instructions labels and lists

## Tests

```bash
pytest tests/
```
