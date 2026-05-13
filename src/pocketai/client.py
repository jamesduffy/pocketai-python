"""Synchronous Pocket client."""

from __future__ import annotations

from types import TracebackType
from typing import Any, Optional, Union

import httpx

from pocketai._client import (
    DEFAULT_BASE_URL,
    DEFAULT_TIMEOUT,
    build_headers,
    drop_none,
    parse_response,
    resolve_api_key,
)
from pocketai.models import (
    AudioUrl,
    Recording,
    RecordingList,
    SearchResults,
    Tag,
    UploadUrl,
)


class _Recordings:
    def __init__(self, client: Pocket) -> None:
        self._client = client

    def list(
        self,
        *,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        tag_ids: Optional[Union[str, list[str]]] = None,
        page: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> RecordingList:
        if isinstance(tag_ids, list):
            tag_ids = ",".join(tag_ids)
        params = drop_none(
            {
                "start_date": start_date,
                "end_date": end_date,
                "tag_ids": tag_ids,
                "page": page,
                "limit": limit,
            }
        )
        body = self._client._request_envelope("GET", "/public/recordings", params=params)
        return RecordingList.model_validate(body)

    def get(
        self,
        recording_id: str,
        *,
        include_transcript: Optional[bool] = None,
        include_summarizations: Optional[bool] = None,
        summarization_id: Optional[str] = None,
    ) -> Recording:
        params = drop_none(
            {
                "include_transcript": _bool_param(include_transcript),
                "include_summarizations": _bool_param(include_summarizations),
                "summarization_id": summarization_id,
            }
        )
        data = self._client._request(
            "GET", f"/public/recordings/{recording_id}", params=params
        )
        return Recording.model_validate(data)

    def audio_url(self, recording_id: str, *, expires_in: Optional[int] = None) -> AudioUrl:
        params = drop_none({"expires_in": expires_in})
        data = self._client._request(
            "GET", f"/public/recordings/{recording_id}/audio-url", params=params
        )
        return AudioUrl.model_validate(data)

    def create_upload_url(
        self,
        *,
        title: Optional[str] = None,
        file_name: Optional[str] = None,
        content_type: Optional[str] = None,
        duration: Optional[float] = None,
        recording_at: Optional[str] = None,
    ) -> UploadUrl:
        json_body = drop_none(
            {
                "title": title,
                "file_name": file_name,
                "content_type": content_type,
                "duration": duration,
                "recording_at": recording_at,
            }
        )
        data = self._client._request(
            "POST", "/public/recordings/upload-url", json=json_body
        )
        return UploadUrl.model_validate(data)


class _Search:
    def __init__(self, client: Pocket) -> None:
        self._client = client

    def query(
        self,
        query: str,
        *,
        limit: Optional[int] = None,
        filters: Optional[dict[str, Any]] = None,
    ) -> SearchResults:
        json_body = drop_none({"query": query, "limit": limit, "filters": filters})
        data = self._client._request("POST", "/public/search", json=json_body)
        return SearchResults.model_validate(data)


class _Tags:
    def __init__(self, client: Pocket) -> None:
        self._client = client

    def list(self) -> list[Tag]:
        data = self._client._request("GET", "/public/tags")
        return [Tag.model_validate(item) for item in (data or [])]


def _bool_param(value: Optional[bool]) -> Optional[str]:
    if value is None:
        return None
    return "true" if value else "false"


class Pocket:
    """Synchronous client for the Pocket Public API.

    Examples
    --------
    >>> client = Pocket(api_key="pk_...")
    >>> page = client.recordings.list(limit=5)
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
        http_client: Optional[httpx.Client] = None,
    ) -> None:
        from pocketai import __version__

        self._api_key = resolve_api_key(api_key)
        self._base_url = base_url.rstrip("/")
        self._owns_http = http_client is None
        self._http = http_client or httpx.Client(
            base_url=self._base_url,
            timeout=timeout,
            headers=build_headers(self._api_key, __version__),
        )
        if http_client is not None:
            for k, v in build_headers(self._api_key, __version__).items():
                self._http.headers.setdefault(k, v)

        self.recordings = _Recordings(self)
        self.search = _Search(self)
        self.tags = _Tags(self)

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[dict[str, Any]] = None,
        json: Optional[dict[str, Any]] = None,
    ) -> Any:
        url = path if path.startswith("http") else self._base_url + path
        response = self._http.request(method, url, params=params, json=json)
        return parse_response(response)

    def _request_envelope(
        self,
        method: str,
        path: str,
        *,
        params: Optional[dict[str, Any]] = None,
        json: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Return the full {data, pagination, ...} envelope rather than just data.

        Used by list endpoints where pagination metadata lives alongside ``data``.
        """
        url = path if path.startswith("http") else self._base_url + path
        response = self._http.request(method, url, params=params, json=json)
        data = parse_response(response)
        body = response.json()
        envelope: dict[str, Any] = {"data": data}
        if isinstance(body, dict) and "pagination" in body:
            envelope["pagination"] = body["pagination"]
        return envelope

    def close(self) -> None:
        if self._owns_http:
            self._http.close()

    def __enter__(self) -> Pocket:
        return self

    def __exit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc: Optional[BaseException],
        tb: Optional[TracebackType],
    ) -> None:
        self.close()
