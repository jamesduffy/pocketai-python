from __future__ import annotations

import json

import httpx
import pytest
import respx

from pocketai import (
    Pocket,
    PocketAuthError,
    PocketError,
    PocketNotFoundError,
    PocketRateLimitError,
    PocketServerError,
)


@respx.mock
def test_list_recordings_parses_envelope(api_key, base_url, fixture):
    payload = fixture("recordings_list")
    respx.get(f"{base_url}/public/recordings").mock(
        return_value=httpx.Response(200, json=payload)
    )

    with Pocket(api_key=api_key) as client:
        page = client.recordings.list(limit=20)

    assert page.pagination.total == 2
    assert page.pagination.has_more is False
    assert [r.title for r in page.data] == ["Sprint backlog review", "Project planning"]
    assert page.data[1].tags[0].name == "planning"


@respx.mock
def test_list_recordings_passes_query_params(api_key, base_url, fixture):
    route = respx.get(f"{base_url}/public/recordings").mock(
        return_value=httpx.Response(200, json=fixture("recordings_list"))
    )

    with Pocket(api_key=api_key) as client:
        client.recordings.list(
            start_date="2026-05-01",
            end_date="2026-05-31",
            tag_ids=["tag-1", "tag-2"],
            page=2,
            limit=50,
        )

    request = route.calls.last.request
    assert request.url.params["start_date"] == "2026-05-01"
    assert request.url.params["end_date"] == "2026-05-31"
    assert request.url.params["tag_ids"] == "tag-1,tag-2"
    assert request.url.params["page"] == "2"
    assert request.url.params["limit"] == "50"


@respx.mock
def test_get_recording_with_transcript(api_key, base_url, fixture):
    rec_id = "11111111-1111-4111-8111-111111111111"
    respx.get(f"{base_url}/public/recordings/{rec_id}").mock(
        return_value=httpx.Response(200, json=fixture("recording_detail"))
    )

    with Pocket(api_key=api_key) as client:
        recording = client.recordings.get(rec_id, include_transcript=True)

    assert recording.id == rec_id
    assert recording.transcript is not None
    assert len(recording.transcript.segments) == 2
    assert recording.transcript.segments[0].text.startswith("Let us start")
    assert recording.transcript.metadata.source == "wizper"


@respx.mock
def test_get_recording_bool_params_serialized(api_key, base_url, fixture):
    rec_id = "11111111-1111-4111-8111-111111111111"
    route = respx.get(f"{base_url}/public/recordings/{rec_id}").mock(
        return_value=httpx.Response(200, json=fixture("recording_detail"))
    )

    with Pocket(api_key=api_key) as client:
        client.recordings.get(rec_id, include_transcript=False, include_summarizations=True)

    request = route.calls.last.request
    assert request.url.params["include_transcript"] == "false"
    assert request.url.params["include_summarizations"] == "true"


@respx.mock
def test_get_recording_with_summarizations(api_key, base_url, fixture):
    rec_id = "11111111-1111-4111-8111-111111111111"
    respx.get(f"{base_url}/public/recordings/{rec_id}").mock(
        return_value=httpx.Response(200, json=fixture("recording_with_summary"))
    )

    with Pocket(api_key=api_key) as client:
        recording = client.recordings.get(rec_id, include_summarizations=True)

    assert recording.summarizations is not None
    summary = recording.summarizations["aa15c2d9-e69e-4f32-a096-797749412dd2"]
    assert summary.processing_status == "completed"
    assert "summary" in summary.v2


@respx.mock
def test_audio_url(api_key, base_url, fixture):
    rec_id = "11111111-1111-4111-8111-111111111111"
    route = respx.get(f"{base_url}/public/recordings/{rec_id}/audio-url").mock(
        return_value=httpx.Response(200, json=fixture("audio_url"))
    )

    with Pocket(api_key=api_key) as client:
        audio = client.recordings.audio_url(rec_id, expires_in=7200)

    assert audio.signed_url.startswith("https://")
    assert audio.expires_in == 3600
    assert route.calls.last.request.url.params["expires_in"] == "7200"


@respx.mock
def test_create_upload_url(api_key, base_url, fixture):
    route = respx.post(f"{base_url}/public/recordings/upload-url").mock(
        return_value=httpx.Response(200, json=fixture("upload_url"))
    )

    with Pocket(api_key=api_key) as client:
        upload = client.recordings.create_upload_url(
            title="My recording",
            file_name="probe.mp3",
            content_type="audio/mpeg",
            duration=120.5,
        )

    assert upload.recording_id == "33333333-3333-4333-8333-333333333333"
    assert upload.upload_url.startswith("https://")
    body = json.loads(route.calls.last.request.content)
    assert body == {
        "title": "My recording",
        "file_name": "probe.mp3",
        "content_type": "audio/mpeg",
        "duration": 120.5,
    }


@respx.mock
def test_search(api_key, base_url, fixture):
    route = respx.post(f"{base_url}/public/search").mock(
        return_value=httpx.Response(200, json=fixture("search"))
    )

    with Pocket(api_key=api_key) as client:
        results = client.search.query("sprint planning", limit=5)

    assert results.total == 1
    assert results.relevant_memories[0].recording_title == "Project planning"
    assert results.relevant_memories[0].relevance_score == pytest.approx(7.35)
    assert results.user_profile.dynamic_context == ["Working on PR review tooling"]
    body = json.loads(route.calls.last.request.content)
    assert body == {"query": "sprint planning", "limit": 5}


@respx.mock
def test_tags_list(api_key, base_url, fixture):
    respx.get(f"{base_url}/public/tags").mock(
        return_value=httpx.Response(200, json=fixture("tags"))
    )

    with Pocket(api_key=api_key) as client:
        tags = client.tags.list()

    assert [t.name for t in tags] == ["planning", "1-on-1"]
    assert tags[0].usage_count == 5


@respx.mock
def test_tags_list_empty(api_key, base_url):
    respx.get(f"{base_url}/public/tags").mock(
        return_value=httpx.Response(200, json={"success": True, "data": []})
    )

    with Pocket(api_key=api_key) as client:
        assert client.tags.list() == []


@respx.mock
def test_unauthorized_raises(api_key, base_url, fixture):
    respx.get(f"{base_url}/public/recordings").mock(
        return_value=httpx.Response(401, json=fixture("error_unauthorized"))
    )

    with Pocket(api_key=api_key) as client, pytest.raises(PocketAuthError) as exc_info:
        client.recordings.list()
    assert exc_info.value.status_code == 401
    assert "API key not found" in exc_info.value.message


@respx.mock
def test_not_found_raises(api_key, base_url, fixture):
    respx.get(f"{base_url}/public/recordings/missing").mock(
        return_value=httpx.Response(404, json=fixture("error_not_found"))
    )

    with Pocket(api_key=api_key) as client, pytest.raises(PocketNotFoundError):
        client.recordings.get("missing")


@respx.mock
def test_rate_limit_raises(api_key, base_url):
    respx.get(f"{base_url}/public/recordings").mock(
        return_value=httpx.Response(429, json={"success": False, "error": "slow down"})
    )

    with Pocket(api_key=api_key) as client, pytest.raises(PocketRateLimitError):
        client.recordings.list()


@respx.mock
def test_server_error_raises(api_key, base_url):
    respx.get(f"{base_url}/public/tags").mock(
        return_value=httpx.Response(503, text="Service Unavailable")
    )

    with Pocket(api_key=api_key) as client, pytest.raises(PocketServerError):
        client.tags.list()


@respx.mock
def test_authorization_header_sent(api_key, base_url, fixture):
    route = respx.get(f"{base_url}/public/tags").mock(
        return_value=httpx.Response(200, json=fixture("tags"))
    )

    with Pocket(api_key=api_key) as client:
        client.tags.list()

    assert route.calls.last.request.headers["Authorization"] == f"Bearer {api_key}"
    assert route.calls.last.request.headers["User-Agent"].startswith("pocketai-python/")


def test_missing_api_key_raises(monkeypatch):
    monkeypatch.delenv("POCKET_API_KEY", raising=False)
    with pytest.raises(PocketError, match="No API key"):
        Pocket()


def test_picks_up_env_api_key(monkeypatch):
    monkeypatch.setenv("POCKET_API_KEY", "pk_env")
    client = Pocket()
    try:
        assert client._api_key == "pk_env"
    finally:
        client.close()
