"""Webhook signature verification and event parsing for Pocket webhooks.

The Pocket webhook signing scheme:

* ``X-HeyPocket-Timestamp`` — Unix timestamp in **milliseconds**
* ``X-HeyPocket-Signature`` — hex digest of ``HMAC-SHA256(secret, f"{timestamp}.{raw_body}")``

Always verify against the **exact raw request body bytes**, before any JSON
parsing or re-serialization.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from typing import Any, Optional, Union

from pydantic import BaseModel, ConfigDict, Field

from pocketai.exceptions import PocketError

DEFAULT_TOLERANCE_SECONDS = 300
"""Reject deliveries whose timestamp differs from local time by more than this."""


class InvalidSignatureError(PocketError):
    """Raised when a webhook delivery fails signature verification."""


def compute_signature(secret: str, timestamp: Union[str, int], body: bytes) -> str:
    """Compute the expected hex HMAC-SHA256 signature for a webhook delivery."""
    secret_bytes = secret if isinstance(secret, bytes) else secret.encode("utf-8")
    payload = f"{timestamp}.".encode() + body
    return hmac.new(secret_bytes, payload, hashlib.sha256).hexdigest()


def verify_signature(
    *,
    secret: str,
    body: bytes,
    timestamp: Union[str, int],
    signature: str,
    tolerance_seconds: Optional[int] = DEFAULT_TOLERANCE_SECONDS,
    now: Optional[float] = None,
) -> None:
    """Verify a webhook delivery, raising ``InvalidSignatureError`` on failure.

    Parameters
    ----------
    secret:
        The webhook signing secret, as configured in Pocket.
    body:
        The raw request body bytes — do not re-serialize JSON.
    timestamp:
        The value of the ``X-HeyPocket-Timestamp`` header (Unix milliseconds).
    signature:
        The value of the ``X-HeyPocket-Signature`` header (hex digest).
    tolerance_seconds:
        Reject deliveries whose timestamp differs from ``now`` by more than this.
        Pass ``None`` to disable freshness checks (not recommended in production).
    now:
        Override the current time for tests. Defaults to ``time.time()``.
    """
    if not isinstance(body, (bytes, bytearray)):
        raise TypeError("body must be bytes; the raw request body, not a string or dict")

    try:
        ts_ms = int(str(timestamp))
    except (TypeError, ValueError) as exc:
        raise InvalidSignatureError(f"invalid timestamp: {timestamp!r}") from exc

    if tolerance_seconds is not None:
        current = now if now is not None else time.time()
        delta = abs(current - (ts_ms / 1000.0))
        if delta > tolerance_seconds:
            raise InvalidSignatureError(
                f"timestamp outside tolerance window ({delta:.0f}s > {tolerance_seconds}s)"
            )

    expected = compute_signature(secret, str(ts_ms), bytes(body))
    if not hmac.compare_digest(expected, signature):
        raise InvalidSignatureError("signature mismatch")


class WebhookEvent(BaseModel):
    """A parsed Pocket webhook event envelope.

    All event-specific fields are forwarded as raw dicts so the consumer can
    pluck them as needed. The schemas of these inner objects evolve over time
    — keeping them as ``dict`` keeps the SDK forward-compatible.
    """

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    event: str
    timestamp: Optional[str] = None
    user: dict[str, Any] = Field(default_factory=dict)
    recording: dict[str, Any] = Field(default_factory=dict)
    summarizations: dict[str, Any] = Field(default_factory=dict)
    transcript: dict[str, Any] = Field(default_factory=dict)
    organization: Optional[dict[str, Any]] = None


def parse_event(body: Union[bytes, str, dict[str, Any]]) -> WebhookEvent:
    """Parse a webhook payload into a :class:`WebhookEvent`."""
    payload = json.loads(body) if isinstance(body, (bytes, bytearray, str)) else body
    return WebhookEvent.model_validate(payload)
