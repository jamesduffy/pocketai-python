from __future__ import annotations

from pocketai.exceptions import (
    PocketAPIError,
    PocketAuthError,
    PocketNotFoundError,
    PocketRateLimitError,
    PocketServerError,
    error_for_status,
)


def test_error_for_status_picks_specific_classes():
    assert isinstance(error_for_status(401, "x", None), PocketAuthError)
    assert isinstance(error_for_status(404, "x", None), PocketNotFoundError)
    assert isinstance(error_for_status(429, "x", None), PocketRateLimitError)
    assert isinstance(error_for_status(500, "x", None), PocketServerError)
    assert isinstance(error_for_status(503, "x", None), PocketServerError)


def test_error_for_status_defaults_to_base_class():
    err = error_for_status(418, "I'm a teapot", {"error": "I'm a teapot"})
    assert type(err) is PocketAPIError
    assert err.status_code == 418
    assert err.response_body == {"error": "I'm a teapot"}


def test_error_str_includes_status_code():
    err = PocketAPIError("boom", status_code=500, response_body=None)
    assert "500" in str(err)
    assert "boom" in str(err)
