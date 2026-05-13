"""Download a recording's audio file using a short-lived signed URL.

Usage:
    python examples/download_audio.py <recording-id>
    python examples/download_audio.py <recording-id> --out meeting.mp3
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import httpx

from pocketai import Pocket


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("recording_id")
    parser.add_argument("--out", type=Path, help="Output path (defaults to <id>.mp3).")
    parser.add_argument(
        "--expires-in",
        type=int,
        default=600,
        help="Signed URL lifetime in seconds (default 600).",
    )
    args = parser.parse_args()

    out_path = args.out or Path(f"{args.recording_id}.mp3")

    with Pocket() as client:
        audio = client.recordings.audio_url(args.recording_id, expires_in=args.expires_in)

    print(f"Signed URL expires at {audio.expires_at} ({audio.expires_in}s).")

    # The signed URL is plain S3 — no Pocket auth needed for the actual byte fetch.
    with httpx.stream("GET", audio.signed_url, timeout=120) as response:
        response.raise_for_status()
        total = int(response.headers.get("content-length", 0))
        downloaded = 0
        with out_path.open("wb") as fh:
            for chunk in response.iter_bytes(chunk_size=1 << 16):
                fh.write(chunk)
                downloaded += len(chunk)
                if total:
                    pct = downloaded / total * 100
                    print(f"\r{downloaded / 1024:>8.1f} KiB / {total / 1024:.1f} KiB ({pct:5.1f}%)",
                          end="", flush=True)
        print()

    print(f"Saved to {out_path}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
