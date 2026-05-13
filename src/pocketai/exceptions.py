"""Exception hierarchy for the Pocket client."""

from __future__ import annotations

from typing import Any, Optional


class PocketError(Exception):
    """Base class for every error raised by this package."""


class PocketAPIError(PocketError):
    """An HTTP response from the Pocket API indicated failure."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int,
        response_body: Optional[Any] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.response_body = response_body

    def __str__(self) -> str:
        return f"[{self.status_code}] {self.message}"


class PocketAuthError(PocketAPIError):
    """401 Unauthorized — missing or invalid API key."""


class PocketNotFoundError(PocketAPIError):
    """404 Not Found — the requested resource does not exist."""


class PocketRateLimitError(PocketAPIError):
    """429 Too Many Requests."""


class PocketServerError(PocketAPIError):
    """5xx response from the Pocket API."""


def error_for_status(status_code: int, message: str, body: Optional[Any]) -> PocketAPIError:
    """Pick the most specific exception class for a given HTTP status."""
    if status_code == 401:
        return PocketAuthError(message, status_code=status_code, response_body=body)
    if status_code == 404:
        return PocketNotFoundError(message, status_code=status_code, response_body=body)
    if status_code == 429:
        return PocketRateLimitError(message, status_code=status_code, response_body=body)
    if 500 <= status_code < 600:
        return PocketServerError(message, status_code=status_code, response_body=body)
    return PocketAPIError(message, status_code=status_code, response_body=body)
