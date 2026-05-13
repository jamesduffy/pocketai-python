"""Upload a local audio file as a new recording and poll until it is processed.

Usage:
    python examples/upload_recording.py /path/to/meeting.mp3
    python examples/upload_recording.py meeting.mp3 --title "Sprint kickoff"
"""

from __future__ import annotations

import argparse
import mimetypes
import sys
import time
from pathlib import Path

import httpx

from pocketai import Pocket


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("audio_path", type=Path)
    parser.add_argument("--title", help="Recording title (defaults to the file name).")
    parser.add_argument(
        "--content-type",
        help="MIME type (auto-detected by extension if omitted).",
    )
    parser.add_argument(
        "--no-wait",
        action="store_true",
        help="Skip polling for processing completion.",
    )
    parser.add_argument(
        "--poll-interval",
        type=float,
        default=5.0,
        help="Seconds between status checks (default 5).",
    )
    args = parser.parse_args()

    audio_path: Path = args.audio_path
    if not audio_path.is_file():
        print(f"No such file: {audio_path}", file=sys.stderr)
        return 1

    content_type = args.content_type or mimetypes.guess_type(audio_path.name)[0] or "audio/mpeg"
    size = audio_path.stat().st_size

    with Pocket() as client:
        upload = client.recordings.create_upload_url(
            title=args.title or audio_path.stem,
            file_name=audio_path.name,
            content_type=content_type,
        )
        print(f"Got upload URL for recording {upload.recording_id} ({size / 1024:.1f} KiB).")

        # PUT the bytes directly to S3 — no Pocket auth on this request.
        with audio_path.open("rb") as fh:
            put_response = httpx.put(
                upload.upload_url,
                content=fh,
                headers={"Content-Type": content_type},
                timeout=300,
            )
        put_response.raise_for_status()
        print("Upload complete.")

        if args.no_wait:
            print(f"Recording id: {upload.recording_id}")
            return 0

        print("Waiting for processing to complete...")
        deadline = time.time() + 10 * 60
        while time.time() < deadline:
            recording = client.recordings.get(
                upload.recording_id,
                include_transcript=False,
                include_summarizations=False,
            )
            print(f"  state = {recording.state}")
            if recording.state == "completed":
                print(f"Done. Recording id: {recording.id}")
                return 0
            if recording.state in {"failed", "error"}:
                print(f"Processing failed (state={recording.state}).", file=sys.stderr)
                return 2
            time.sleep(args.poll_interval)

        print("Timed out waiting for processing.", file=sys.stderr)
        return 3


if __name__ == "__main__":
    sys.exit(main())
