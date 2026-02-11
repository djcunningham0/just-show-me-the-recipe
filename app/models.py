from pydantic import BaseModel


class Recipe(BaseModel):
    title: str
    source_url: str
    servings: str | None = None
    prep_time: str | None = None
    cook_time: str | None = None
    image_url: str | None = None
    ingredients: list[str]
    steps: list[str]


class ParseError(Exception):
    def __init__(self, error_type: str, message: str):
        self.error_type = error_type
        self.message = message
        super().__init__(message)
