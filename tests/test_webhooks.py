from __future__ import annotations

import hashlib
import hmac
import json
import time

import pytest

from pocketai.webhooks import (
    InvalidSignatureError,
    WebhookEvent,
    compute_signature,
    parse_event,
    verify_signature,
)

SECRET = "whsec_test_secret"


def _sign(secret: str, timestamp: str, body: bytes) -> str:
    payload = f"{timestamp}.".encode() + body
    return hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()


def test_compute_signature_matches_reference():
    body = b'{"event":"summary.completed"}'
    ts = "1747091000000"
    assert compute_signature(SECRET, ts, body) == _sign(SECRET, ts, body)


def test_verify_signature_valid():
    body = b'{"event":"summary.completed"}'
    now = 1747091000.0
    ts = str(int(now * 1000))
    sig = _sign(SECRET, ts, body)

    verify_signature(secret=SECRET, body=body, timestamp=ts, signature=sig, now=now)


def test_verify_signature_rejects_tampered_body():
    body = b'{"event":"summary.completed"}'
    tampered = b'{"event":"recording.deleted"}'
    now = 1747091000.0
    ts = str(int(now * 1000))
    sig = _sign(SECRET, ts, body)

    with pytest.raises(InvalidSignatureError, match="signature mismatch"):
        verify_signature(
            secret=SECRET, body=tampered, timestamp=ts, signature=sig, now=now
        )


def test_verify_signature_rejects_wrong_secret():
    body = b'{"event":"summary.completed"}'
    now = 1747091000.0
    ts = str(int(now * 1000))
    sig = _sign("other_secret", ts, body)

    with pytest.raises(InvalidSignatureError):
        verify_signature(secret=SECRET, body=body, timestamp=ts, signature=sig, now=now)


def test_verify_signature_rejects_stale_timestamp():
    body = b'{"event":"summary.completed"}'
    now = 1747091000.0
    ts = str(int((now - 3600) * 1000))  # one hour old
    sig = _sign(SECRET, ts, body)

    with pytest.raises(InvalidSignatureError, match="outside tolerance"):
        verify_signature(
            secret=SECRET,
            body=body,
            timestamp=ts,
            signature=sig,
            tolerance_seconds=300,
            now=now,
        )


def test_verify_signature_accepts_skipped_freshness():
    body = b'{"event":"summary.completed"}'
    now = 1747091000.0
    ts = str(int((now - 86400) * 1000))
    sig = _sign(SECRET, ts, body)

    verify_signature(
        secret=SECRET,
        body=body,
        timestamp=ts,
        signature=sig,
        tolerance_seconds=None,
        now=now,
    )


def test_verify_signature_rejects_invalid_timestamp():
    body = b'{}'
    with pytest.raises(InvalidSignatureError, match="invalid timestamp"):
        verify_signature(secret=SECRET, body=body, timestamp="not-a-number", signature="x")


def test_verify_signature_rejects_non_bytes_body():
    with pytest.raises(TypeError, match="bytes"):
        verify_signature(
            secret=SECRET,
            body="a string, not bytes",  # type: ignore[arg-type]
            timestamp=str(int(time.time() * 1000)),
            signature="x",
        )


def test_verify_signature_with_integer_timestamp():
    body = b"{}"
    now = 1747091000.0
    ts_int = int(now * 1000)
    sig = _sign(SECRET, str(ts_int), body)

    verify_signature(secret=SECRET, body=body, timestamp=ts_int, signature=sig, now=now)


def test_parse_event_from_bytes():
    payload = {
        "event": "summary.completed",
        "timestamp": "2026-05-12T12:00:00Z",
        "user": {"id": "user-1"},
        "recording": {"id": "rec-1", "title": "Sync"},
        "summarizations": {},
        "transcript": {},
    }
    event = parse_event(json.dumps(payload).encode("utf-8"))
    assert isinstance(event, WebhookEvent)
    assert event.event == "summary.completed"
    assert event.recording["id"] == "rec-1"


def test_parse_event_preserves_unknown_fields():
    payload = {
        "event": "recording.created",
        "extra_field": {"future": True},
        "recording": {"id": "rec-2"},
    }
    event = parse_event(payload)
    assert event.event == "recording.created"
    assert event.model_extra["extra_field"] == {"future": True}
