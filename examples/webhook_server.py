"""Minimal Flask app that receives Pocket webhooks, verifies them, and dispatches.

Setup:
    pip install pocketai flask
    export POCKET_WEBHOOK_SECRET=whsec_xxx
    python examples/webhook_server.py
    # Then point a Pocket webhook integration at http://<your-host>/pocket-webhook

The handler:
  1. Reads the **raw** request body bytes (do not let any middleware re-serialize).
  2. Verifies the HMAC-SHA256 signature against the documented timestamp + body scheme.
  3. Parses the payload into a typed ``WebhookEvent`` and dispatches by event name.
"""

from __future__ import annotations

import logging
import os
import sys

try:
    from flask import Flask, abort, request
except ImportError as exc:  # pragma: no cover - example-only dep
    print("This example needs Flask: pip install flask", file=sys.stderr)
    raise SystemExit(1) from exc

from pocketai.webhooks import InvalidSignatureError, parse_event, verify_signature

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("pocket-webhooks")

SECRET = os.environ.get("POCKET_WEBHOOK_SECRET")
if not SECRET:
    print("Set POCKET_WEBHOOK_SECRET in the environment.", file=sys.stderr)
    sys.exit(1)

app = Flask(__name__)


@app.post("/pocket-webhook")
def pocket_webhook() -> tuple[str, int]:
    body = request.get_data()  # raw bytes — what Pocket actually signed
    timestamp = request.headers.get("X-HeyPocket-Timestamp")
    signature = request.headers.get("X-HeyPocket-Signature")
    if not (timestamp and signature):
        abort(400, "Missing signature headers")

    try:
        verify_signature(
            secret=SECRET,
            body=body,
            timestamp=timestamp,
            signature=signature,
        )
    except InvalidSignatureError as exc:
        log.warning("Rejected webhook delivery: %s", exc)
        abort(401)

    event = parse_event(body)
    log.info("event=%s recording=%s", event.event, event.recording.get("id"))

    if event.event == "recording.created":
        handle_recording_created(event)
    elif event.event == "transcription.completed":
        handle_transcription_completed(event)
    elif event.event == "summary.completed":
        handle_summary_completed(event)
    else:
        log.info("unhandled event %s", event.event)

    return "", 204


def handle_recording_created(event):
    log.info("new recording: %r", event.recording.get("title"))


def handle_transcription_completed(event):
    segments = event.transcript.get("segments", []) if event.transcript else []
    log.info("transcription ready: %d segments", len(segments))


def handle_summary_completed(event):
    log.info("summary ready for recording %s", event.recording.get("id"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
