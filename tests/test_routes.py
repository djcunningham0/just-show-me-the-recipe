"""Tests for FastAPI route handlers."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models import ParseError, Recipe


@pytest.fixture()
def client():
    return TestClient(app)


SAMPLE_RECIPE = Recipe(
    title="Test Soup",
    source_url="https://example.com/soup",
    ingredients=["water", "salt"],
    steps=["Boil water.", "Add salt."],
)


# -- Homepage --


def test_homepage_returns_200(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "Just Show Me the Recipe" in resp.text or "<form" in resp.text


# -- Recipe route: success --


@patch("app.main.parse_recipe", new_callable=AsyncMock)
def test_recipe_success(mock_parse, client):
    mock_parse.return_value = SAMPLE_RECIPE
    resp = client.get("/recipe", params={"url": "https://example.com/soup"})
    assert resp.status_code == 200
    assert "Test Soup" in resp.text
    assert "water" in resp.text
    assert "Boil water." in resp.text


# -- Recipe route: parse errors --


@patch("app.main.parse_recipe", new_callable=AsyncMock)
def test_recipe_parse_error(mock_parse, client):
    mock_parse.side_effect = ParseError("parse", "No recipe found on that page.")
    resp = client.get("/recipe", params={"url": "https://example.com/blog"})
    assert resp.status_code == 200  # error template, not HTTP error
    assert "No recipe found" in resp.text


@patch("app.main.parse_recipe", new_callable=AsyncMock)
def test_recipe_network_error(mock_parse, client):
    mock_parse.side_effect = ParseError("network", "Request timed out.")
    resp = client.get("/recipe", params={"url": "https://example.com/slow"})
    assert resp.status_code == 200
    assert "timed out" in resp.text


# -- Missing URL parameter --


def test_recipe_missing_url(client):
    resp = client.get("/recipe")
    assert resp.status_code == 422  # FastAPI validation error


# -- Security headers --


def test_security_headers(client):
    resp = client.get("/")
    assert resp.headers["X-Content-Type-Options"] == "nosniff"
    assert resp.headers["X-Frame-Options"] == "DENY"
    assert resp.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
