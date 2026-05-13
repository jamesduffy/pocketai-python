"""Pydantic models for Pocket API responses."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class _Model(BaseModel):
    """Base model — tolerant of unknown fields so the API can evolve."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)


class Tag(_Model):
    id: Optional[str] = None
    name: Optional[str] = None
    color: Optional[str] = None
    usage_count: Optional[int] = None


class TranscriptSegment(_Model):
    start: float
    end: float
    text: str
    original_text: Optional[str] = Field(default=None, alias="originalText")
    speaker: Optional[str] = None


class TranscriptMetadata(_Model):
    duration: Optional[float] = None
    language: Optional[str] = None
    language_probability: Optional[float] = None
    source: Optional[str] = None


class Transcript(_Model):
    metadata: Optional[TranscriptMetadata] = None
    segments: list[TranscriptSegment] = Field(default_factory=list)


class RecordingSummary(_Model):
    """A single summarization output for a recording.

    The Pocket API returns summarizations as an object keyed by
    summarization template id; each value is one of these.
    """

    id: Optional[str] = None
    summarization_id: Optional[str] = Field(default=None, alias="summarizationId")
    processing_status: Optional[str] = Field(default=None, alias="processingStatus")
    v2: Optional[dict[str, Any]] = None


class Recording(_Model):
    id: str
    title: Optional[str] = None
    duration: Optional[float] = None
    state: Optional[str] = None
    language: Optional[str] = None
    recording_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    tags: list[Tag] = Field(default_factory=list)
    transcript: Optional[Transcript] = None
    summarizations: Optional[dict[str, RecordingSummary]] = None


class Pagination(_Model):
    page: int
    limit: int
    total: int
    total_pages: int
    has_more: bool


class RecordingList(_Model):
    data: list[Recording] = Field(default_factory=list)
    pagination: Pagination


class AudioUrl(_Model):
    signed_url: str
    expires_in: int
    expires_at: Optional[datetime] = None


class UploadUrl(_Model):
    recording_id: str
    s3_key: str
    upload_url: str
    expires_in: int


class SearchMemory(_Model):
    content: str
    language: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    recording_date: Optional[datetime] = Field(default=None, alias="recordingDate")
    recording_id: Optional[str] = Field(default=None, alias="recordingId")
    recording_title: Optional[str] = Field(default=None, alias="recordingTitle")
    relevance_score: Optional[float] = Field(default=None, alias="relevanceScore")
    speakers: Optional[str] = None
    transcription_id: Optional[str] = Field(default=None, alias="transcriptionId")


class SearchUserProfile(_Model):
    dynamic_context: list[str] = Field(default_factory=list, alias="dynamicContext")
    static_facts: list[str] = Field(default_factory=list, alias="staticFacts")


class SearchResults(_Model):
    user_profile: Optional[SearchUserProfile] = Field(default=None, alias="userProfile")
    relevant_memories: list[SearchMemory] = Field(default_factory=list, alias="relevantMemories")
    total: int = 0
    timing: Optional[float] = None
