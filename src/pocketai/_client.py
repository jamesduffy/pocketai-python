"""Shared HTTP plumbing for the sync and async clients."""

from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Any, Optional

import httpx

from pocketai.exceptions import PocketError, error_for_status

DEFAULT_BASE_URL = "https://public.heypocketai.com/api/v1"
DEFAULT_TIMEOUT = 30.0
USER_AGENT = "pocketai-python"


def resolve_api_key(api_key: Optional[str]) -> str:
    """Return an API key from the argument or POCKET_API_KEY in the environment."""
    if api_key is None:
        api_key = os.environ.get("POCKET_API_KEY")
    if not api_key:
        raise PocketError(
            "No API key provided. Pass api_key='pk_...' or set POCKET_API_KEY."
        )
    return api_key


def build_headers(api_key: str, version: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
        "User-Agent": f"{USER_AGENT}/{version}",
    }


def parse_response(response: httpx.Response) -> Any:
    """Parse a Pocket API response, raising on errors.

    The API wraps every payload in {"success": bool, "data": ..., "error": "..."}.
    On success this returns the unwrapped ``data`` field. On failure it raises a
    typed PocketAPIError subclass.
    """
    try:
        body = response.json()
    except ValueError:
        body = None

    if response.is_success and isinstance(body, dict) and body.get("success") is True:
        return body.get("data")

    if isinstance(body, dict):
        message = body.get("error") or body.get("message") or response.reason_phrase or "API error"
    else:
        message = response.reason_phrase or f"HTTP {response.status_code}"

    raise error_for_status(response.status_code, str(message), body)


def drop_none(mapping: Mapping[str, Any]) -> dict[str, Any]:
    """Return a copy of ``mapping`` without keys whose value is None."""
    return {k: v for k, v in mapping.items() if v is not None}
