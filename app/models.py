import html

from pydantic import BaseModel, model_validator


class ParsedIngredient(BaseModel):
    """Structured ingredient data extracted from a raw ingredient string."""

    raw: str
    amount: float | None = None
    amount_max: float | None = None
    unit: str | None = None
    name: str
    preparation: str | None = None
    comment: str | None = None


class Recipe(BaseModel):
    title: str
    source_url: str
    servings: str | None = None
    prep_time: str | None = None
    cook_time: str | None = None
    image_url: str | None = None
    ingredients: list[str]
    parsed_ingredients: list[ParsedIngredient] | None = None
    steps: list[str]

    @model_validator(mode="after")
    def clean_text(self) -> "Recipe":
        """Decode HTML entities and strip whitespace from text fields."""
        self.title = html.unescape(self.title).strip()
        self.ingredients = [html.unescape(s).strip() for s in self.ingredients]
        self.steps = [html.unescape(s).strip() for s in self.steps]
        return self


class ParseError(Exception):
    def __init__(self, error_type: str, message: str):
        self.error_type = error_type
        self.message = message
        super().__init__(message)
