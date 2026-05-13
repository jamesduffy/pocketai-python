"""Full local backup of every recording your API key can see.

For each recording the script writes::

    <out>/recordings/<id>/recording.json    # raw API payload
    <out>/recordings/<id>/transcript.md     # readable transcript
    <out>/recordings/<id>/summary.md        # readable summaries (if any)
    <out>/recordings/<id>/audio.mp3         # audio bytes

Plus top-level ``tags.json`` and ``manifest.json``.

The script is **resumable**: a recording whose ``updated_at`` matches the
local ``recording.json`` is skipped. Re-running picks up only new or
changed recordings.

Usage:
    python examples/backup.py
    python examples/backup.py --out ~/pocket-archive --concurrency 8
    python examples/backup.py --since 2026-01-01 --no-audio
    python examples/backup.py --force  # re-download everything
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import textwrap
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import httpx

from pocketai import AsyncPocket, Recording


@dataclass
class Stats:
    total_listed: int = 0
    fetched: int = 0
    skipped_unchanged: int = 0
    audio_downloaded: int = 0
    audio_skipped: int = 0
    errors: list[str] = field(default_factory=list)


def _format_timestamp(seconds: float) -> str:
    minutes, secs = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours:d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:d}:{secs:02d}"


def _existing_updated_at(recording_dir: Path) -> Optional[datetime]:
    """Return the ``updated_at`` recorded on disk, or None if no prior backup."""
    path = recording_dir / "recording.json"
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text())
        raw = payload.get("updated_at")
        if not raw:
            return None
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except (OSError, json.JSONDecodeError, ValueError):
        return None


def _write_transcript_md(recording: Recording, path: Path) -> None:
    if recording.transcript is None or not recording.transcript.segments:
        path.write_text(f"# {recording.title or recording.id}\n\n_No transcript available._\n")
        return

    lines = [
        f"# {recording.title or recording.id}",
        "",
        f"- **Recording ID:** `{recording.id}`",
        f"- **Recorded at:** {recording.recording_at}",
        f"- **Duration:** {(recording.duration or 0) / 60:.1f} min",
        f"- **Language:** {recording.language}",
        "",
        "## Transcript",
        "",
    ]
    for segment in recording.transcript.segments:
        ts = _format_timestamp(segment.start)
        speaker = f"**{segment.speaker}:** " if segment.speaker else ""
        lines.append(f"`[{ts}]` {speaker}{segment.text}")
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_summary_md(recording: Recording, path: Path) -> None:
    if not recording.summarizations:
        path.write_text(f"# {recording.title or recording.id}\n\n_No summaries available._\n")
        return

    lines = [f"# {recording.title or recording.id}", ""]
    for sum_id, summary in recording.summarizations.items():
        lines.append(f"## Summarization `{sum_id}`")
        lines.append("")
        lines.append(f"- **Status:** {summary.processing_status}")
        lines.append("")
        markdown = None
        if summary.v2 and isinstance(summary.v2.get("summary"), dict):
            markdown = summary.v2["summary"].get("markdown")
        if markdown:
            lines.append(markdown)
        else:
            lines.append("_(no markdown body)_")
        lines.append("")
        if summary.v2 and summary.v2.get("action_items"):
            lines.append("### Action items")
            lines.append("")
            for item in summary.v2["action_items"]:
                if isinstance(item, dict):
                    text = item.get("text") or json.dumps(item)
                else:
                    text = str(item)
                lines.append(f"- {text}")
            lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


async def _download_audio(
    client: AsyncPocket,
    http: httpx.AsyncClient,
    recording_id: str,
    path: Path,
) -> None:
    audio = await client.recordings.audio_url(recording_id, expires_in=1800)
    tmp = path.with_suffix(path.suffix + ".part")
    async with http.stream("GET", audio.signed_url, timeout=600) as response:
        response.raise_for_status()
        with tmp.open("wb") as fh:
            async for chunk in response.aiter_bytes(1 << 16):
                fh.write(chunk)
    tmp.replace(path)


async def _backup_one(
    client: AsyncPocket,
    http: httpx.AsyncClient,
    summary_listing: Recording,
    out_root: Path,
    stats: Stats,
    sem: asyncio.Semaphore,
    *,
    fetch_audio: bool,
    force: bool,
) -> None:
    async with sem:
        rec_dir = out_root / "recordings" / summary_listing.id
        rec_dir.mkdir(parents=True, exist_ok=True)

        existing_updated_at = _existing_updated_at(rec_dir)
        unchanged = (
            not force
            and existing_updated_at is not None
            and summary_listing.updated_at is not None
            and existing_updated_at == summary_listing.updated_at
        )

        if unchanged:
            stats.skipped_unchanged += 1
        else:
            try:
                recording = await client.recordings.get(
                    summary_listing.id,
                    include_transcript=True,
                    include_summarizations=True,
                )
            except Exception as exc:  # noqa: BLE001
                stats.errors.append(f"{summary_listing.id}: detail fetch failed: {exc}")
                return

            (rec_dir / "recording.json").write_text(
                recording.model_dump_json(indent=2, by_alias=False, exclude_none=False)
            )
            _write_transcript_md(recording, rec_dir / "transcript.md")
            _write_summary_md(recording, rec_dir / "summary.md")
            stats.fetched += 1

        if fetch_audio:
            audio_path = rec_dir / "audio.mp3"
            if audio_path.exists() and not force:
                stats.audio_skipped += 1
            else:
                try:
                    await _download_audio(client, http, summary_listing.id, audio_path)
                    stats.audio_downloaded += 1
                except httpx.HTTPStatusError as exc:
                    # Recordings without an uploaded audio file return 404 here — that's normal.
                    if exc.response.status_code == 404:
                        stats.audio_skipped += 1
                    else:
                        stats.errors.append(f"{summary_listing.id}: audio download failed: {exc}")
                except Exception as exc:  # noqa: BLE001
                    stats.errors.append(f"{summary_listing.id}: audio download failed: {exc}")


async def main_async(args: argparse.Namespace) -> int:
    out_root: Path = args.out.expanduser().resolve()
    out_root.mkdir(parents=True, exist_ok=True)
    (out_root / "recordings").mkdir(exist_ok=True)

    stats = Stats()

    async with AsyncPocket() as client:
        tags = await client.tags.list()
        (out_root / "tags.json").write_text(
            json.dumps([t.model_dump(by_alias=False) for t in tags], indent=2, default=str)
        )
        print(f"Saved {len(tags)} tags.")

        listings: list[Recording] = []
        page_num = 1
        while True:
            page = await client.recordings.list(
                start_date=args.since,
                end_date=args.until,
                page=page_num,
                limit=100,
            )
            listings.extend(page.data)
            if not page.pagination.has_more:
                break
            page_num += 1

        stats.total_listed = len(listings)
        print(f"Listed {stats.total_listed} recordings. Starting backup...")

        sem = asyncio.Semaphore(args.concurrency)
        async with httpx.AsyncClient() as http:
            await asyncio.gather(
                *[
                    _backup_one(
                        client,
                        http,
                        rec,
                        out_root,
                        stats,
                        sem,
                        fetch_audio=not args.no_audio,
                        force=args.force,
                    )
                    for rec in listings
                ]
            )

    manifest: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "filters": {"since": args.since, "until": args.until, "no_audio": args.no_audio},
        "stats": {
            "total_listed": stats.total_listed,
            "fetched": stats.fetched,
            "skipped_unchanged": stats.skipped_unchanged,
            "audio_downloaded": stats.audio_downloaded,
            "audio_skipped": stats.audio_skipped,
            "errors": stats.errors,
        },
    }
    (out_root / "manifest.json").write_text(json.dumps(manifest, indent=2))

    print(textwrap.dedent(f"""
        Backup complete -> {out_root}
          listed:            {stats.total_listed}
          newly fetched:     {stats.fetched}
          unchanged:         {stats.skipped_unchanged}
          audio downloaded:  {stats.audio_downloaded}
          audio skipped:     {stats.audio_skipped}
          errors:            {len(stats.errors)}
    """).strip())
    if stats.errors:
        print("\nErrors:")
        for err in stats.errors:
            print(f"  - {err}")
    return 1 if stats.errors else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path("pocket-backup"))
    parser.add_argument("--since", help="YYYY-MM-DD, UTC")
    parser.add_argument("--until", help="YYYY-MM-DD, UTC")
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--no-audio", action="store_true", help="Skip MP3 downloads.")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-fetch and re-download even if the recording is unchanged.",
    )
    args = parser.parse_args()
    return asyncio.run(main_async(args))


if __name__ == "__main__":
    sys.exit(main())
