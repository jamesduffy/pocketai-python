from __future__ import annotations

from datetime import datetime, timezone

from pocketai.models import (
    Recording,
    RecordingList,
    SearchResults,
    TranscriptSegment,
)


def test_recording_parses_iso_datetimes(fixture):
    rec = Recording.model_validate(fixture("recording_detail")["data"])
    assert rec.recording_at == datetime(2026, 5, 12, 20, 32, 14, tzinfo=timezone.utc)
    assert rec.transcript is not None
    assert isinstance(rec.transcript.segments[0], TranscriptSegment)


def test_recording_list_round_trips(fixture):
    payload = fixture("recordings_list")
    page = RecordingList.model_validate(payload)
    assert page.pagination.total == 2
    dumped = page.model_dump(mode="json")
    assert dumped["pagination"]["total"] == 2


def test_search_results_alias_handling(fixture):
    res = SearchResults.model_validate(fixture("search")["data"])
    assert res.relevant_memories[0].recording_id == "22222222-2222-4222-8222-222222222222"
    assert res.relevant_memories[0].relevance_score is not None


def test_recording_tolerates_extra_fields(fixture):
    payload = fixture("recording_detail")["data"]
    payload["future_field"] = {"unknown": True}
    rec = Recording.model_validate(payload)
    assert rec.model_extra["future_field"] == {"unknown": True}
