# pocketai

An unofficial Python client for the [Pocket](https://heypocketai.com) Public API. Sync and async, fully typed, with first-class webhook signature verification.

```bash
pip install pocketai
```

## Quickstart

```python
from pocketai import Pocket

client = Pocket(api_key="pk_...")  # or set POCKET_API_KEY in the env

# List recordings (paginated)
page = client.recordings.list(limit=20)
for rec in page.data:
    print(rec.id, rec.title, rec.duration)

# Get a single recording with transcript and summarizations
recording = client.recordings.get(
    "cdbac0c1-92bd-41e6-bfa3-f58ce029bd44",
    include_transcript=True,
    include_summarizations=True,
)

# Get a short-lived signed URL to download the audio
audio = client.recordings.audio_url(recording.id, expires_in=3600)
print(audio.signed_url)

# Create an upload URL for a new recording
upload = client.recordings.create_upload_url(
    title="Team sync",
    file_name="team-sync.mp3",
    content_type="audio/mpeg",
)
# PUT the bytes to upload.upload_url, then poll client.recordings.get(upload.recording_id).

# Semantic search across your recordings
results = client.search.query("sprint planning", limit=10)
for memory in results.relevant_memories:
    print(memory.recording_title, memory.relevance_score)

# List tags
tags = client.tags.list()
```

### Async

```python
import asyncio
from pocketai import AsyncPocket

async def main():
    async with AsyncPocket(api_key="pk_...") as client:
        page = await client.recordings.list(limit=5)
        print([r.title for r in page.data])

asyncio.run(main())
```

### Errors

Every non-2xx response raises a typed exception derived from `PocketError`:

```python
from pocketai import Pocket, PocketAuthError, PocketNotFoundError, PocketRateLimitError

client = Pocket(api_key="pk_bad")
try:
    client.recordings.list()
except PocketAuthError as exc:
    print(exc.status_code, exc.message)
```

## Webhooks

Verify Pocket webhook deliveries:

```python
from pocketai.webhooks import InvalidSignatureError, parse_event, verify_signature

@app.post("/pocket-webhook")
def handler(request):
    body = request.body  # raw bytes — do not re-serialize
    try:
        verify_signature(
            secret=WEBHOOK_SECRET,
            body=body,
            timestamp=request.headers["X-HeyPocket-Timestamp"],
            signature=request.headers["X-HeyPocket-Signature"],
        )
    except InvalidSignatureError:
        return 401

    event = parse_event(body)
    if event.event == "summary.completed":
        print(event.recording["id"])
    return 200
```

The signature scheme is `HMAC-SHA256(secret, f"{timestamp}.{raw_body}")` returning hex; verification is constant-time and rejects timestamps older than 5 minutes by default (configurable via `tolerance_seconds`).

## API coverage

| Resource | Method | Endpoint |
|---|---|---|
| Recordings | `recordings.list` | `GET /public/recordings` |
| Recordings | `recordings.get` | `GET /public/recordings/{id}` |
| Recordings | `recordings.audio_url` | `GET /public/recordings/{id}/audio-url` |
| Recordings | `recordings.create_upload_url` | `POST /public/recordings/upload-url` |
| Search | `search.query` | `POST /public/search` |
| Tags | `tags.list` | `GET /public/tags` |

Organization admin endpoints (members, templates, analytics, webhook management) are not yet covered — contributions welcome.

## Development

```bash
pip install -e .[dev]
pytest
mypy
ruff check src tests
```

Tests are fully offline; live API responses are mocked via `respx` against captured response shapes.

## License

MIT
