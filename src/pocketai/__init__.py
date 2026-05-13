"""Python client for the Pocket (heypocketai.com) Public API."""

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _installed_version

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

try:
    __version__ = _installed_version("pocketai")
except PackageNotFoundError:  # running from an un-installed source checkout
    __version__ = "0.0.0+unknown"

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
