"""Export a single recording's transcript as a Markdown file with timestamps.

Usage:
    python examples/export_transcript.py <recording-id>
    python examples/export_transcript.py <recording-id> --out my-meeting.md
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from pocketai import Pocket


def _format_timestamp(seconds: float) -> str:
    minutes, secs = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours:d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:d}:{secs:02d}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("recording_id")
    parser.add_argument("--out", type=Path, help="Output file (defaults to <id>.md).")
    args = parser.parse_args()

    out_path = args.out or Path(f"{args.recording_id}.md")

    with Pocket() as client:
        recording = client.recordings.get(
            args.recording_id,
            include_transcript=True,
            include_summarizations=False,
        )

    if recording.transcript is None or not recording.transcript.segments:
        print(f"Recording {args.recording_id} has no transcript yet.", file=sys.stderr)
        return 1

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

    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {out_path} ({len(recording.transcript.segments)} segments).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
