from __future__ import annotations

import httpx
import pytest
import respx

from pocketai import AsyncPocket, PocketAuthError, PocketNotFoundError


@respx.mock
async def test_async_list_recordings(api_key, base_url, fixture):
    respx.get(f"{base_url}/public/recordings").mock(
        return_value=httpx.Response(200, json=fixture("recordings_list"))
    )

    async with AsyncPocket(api_key=api_key) as client:
        page = await client.recordings.list(limit=20)

    assert page.pagination.total == 2
    assert page.data[0].id == "11111111-1111-4111-8111-111111111111"


@respx.mock
async def test_async_get_recording(api_key, base_url, fixture):
    rec_id = "11111111-1111-4111-8111-111111111111"
    respx.get(f"{base_url}/public/recordings/{rec_id}").mock(
        return_value=httpx.Response(200, json=fixture("recording_detail"))
    )

    async with AsyncPocket(api_key=api_key) as client:
        recording = await client.recordings.get(rec_id, include_transcript=True)

    assert recording.title == "Sprint backlog review"


@respx.mock
async def test_async_audio_url(api_key, base_url, fixture):
    rec_id = "11111111-1111-4111-8111-111111111111"
    respx.get(f"{base_url}/public/recordings/{rec_id}/audio-url").mock(
        return_value=httpx.Response(200, json=fixture("audio_url"))
    )

    async with AsyncPocket(api_key=api_key) as client:
        audio = await client.recordings.audio_url(rec_id)

    assert audio.signed_url.startswith("https://")


@respx.mock
async def test_async_create_upload_url(api_key, base_url, fixture):
    respx.post(f"{base_url}/public/recordings/upload-url").mock(
        return_value=httpx.Response(200, json=fixture("upload_url"))
    )

    async with AsyncPocket(api_key=api_key) as client:
        upload = await client.recordings.create_upload_url(title="Async upload")

    assert upload.recording_id.startswith("3333")


@respx.mock
async def test_async_search(api_key, base_url, fixture):
    respx.post(f"{base_url}/public/search").mock(
        return_value=httpx.Response(200, json=fixture("search"))
    )

    async with AsyncPocket(api_key=api_key) as client:
        results = await client.search.query("planning")

    assert results.total == 1


@respx.mock
async def test_async_tags(api_key, base_url, fixture):
    respx.get(f"{base_url}/public/tags").mock(
        return_value=httpx.Response(200, json=fixture("tags"))
    )

    async with AsyncPocket(api_key=api_key) as client:
        tags = await client.tags.list()

    assert len(tags) == 2


@respx.mock
async def test_async_unauthorized(api_key, base_url, fixture):
    respx.get(f"{base_url}/public/recordings").mock(
        return_value=httpx.Response(401, json=fixture("error_unauthorized"))
    )

    async with AsyncPocket(api_key=api_key) as client:
        with pytest.raises(PocketAuthError):
            await client.recordings.list()


@respx.mock
async def test_async_not_found(api_key, base_url, fixture):
    respx.get(f"{base_url}/public/recordings/missing").mock(
        return_value=httpx.Response(404, json=fixture("error_not_found"))
    )

    async with AsyncPocket(api_key=api_key) as client:
        with pytest.raises(PocketNotFoundError):
            await client.recordings.get("missing")
