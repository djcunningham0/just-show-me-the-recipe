"""Tests for URL validation and SSRF protection."""

import pytest

from app.models import ParseError
from app.parser.pipeline import validate_url

# -- Blocked schemes --


def test_rejects_file_scheme():
    with pytest.raises(ParseError, match="Only http and https"):
        validate_url("file:///etc/passwd")


def test_rejects_ftp_scheme():
    with pytest.raises(ParseError, match="Only http and https"):
        validate_url("ftp://example.com/file.txt")


def test_rejects_no_scheme():
    with pytest.raises(ParseError, match="Only http and https"):
        validate_url("example.com/recipe")


# -- Blocked private/internal IPs --


def test_rejects_localhost():
    with pytest.raises(ParseError, match="private or internal"):
        validate_url("http://127.0.0.1/")


def test_rejects_localhost_name():
    with pytest.raises(ParseError, match="private or internal"):
        validate_url("http://localhost/")


def test_rejects_class_a_private():
    with pytest.raises(ParseError, match="private or internal"):
        validate_url("http://10.0.0.1/")


def test_rejects_class_b_private():
    with pytest.raises(ParseError, match="private or internal"):
        validate_url("http://172.16.0.1/")


def test_rejects_class_c_private():
    with pytest.raises(ParseError, match="private or internal"):
        validate_url("http://192.168.1.1/")


def test_rejects_link_local_metadata():
    with pytest.raises(ParseError, match="private or internal"):
        validate_url("http://169.254.169.254/latest/meta-data/")


# -- Invalid URLs --


def test_rejects_empty_string():
    with pytest.raises(ParseError):
        validate_url("")


def test_rejects_garbage():
    with pytest.raises(ParseError):
        validate_url("not-a-url-at-all")


# -- Valid URLs --


def test_accepts_http():
    validate_url("http://example.com/recipe")


def test_accepts_https():
    validate_url("https://www.allrecipes.com/recipe/12345")
