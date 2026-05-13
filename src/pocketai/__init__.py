"""Python client for the Pocket (heypocketai.com) Public API."""

from pocketai._client import DEFAULT_BASE_URL
from pocketai.async_client import AsyncPocket
from pocketai.client import Pocket
from pocketai.exceptions import (
    PocketAPIError,
    PocketAuthError,
    PocketError,
    PocketNotFoundError,
    PocketRateLimitError,
    PocketServerError,
)
from pocketai.models import (
    AudioUrl,
    Pagination,
    Recording,
    RecordingList,
    RecordingSummary,
    SearchMemory,
    SearchResults,
    Tag,
    TranscriptSegment,
    UploadUrl,
)

__version__ = "0.1.0"

__all__ = [
    "DEFAULT_BASE_URL",
    "AsyncPocket",
    "AudioUrl",
    "Pagination",
    "Pocket",
    "PocketAPIError",
    "PocketAuthError",
    "PocketError",
    "PocketNotFoundError",
    "PocketRateLimitError",
    "PocketServerError",
    "Recording",
    "RecordingList",
    "RecordingSummary",
    "SearchMemory",
    "SearchResults",
    "Tag",
    "TranscriptSegment",
    "UploadUrl",
    "__version__",
]
