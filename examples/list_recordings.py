"""List recordings, with optional date and tag filters.

Usage:
    python examples/list_recordings.py
    python examples/list_recordings.py --since 2026-05-01 --until 2026-05-31
    python examples/list_recordings.py --tag <tag-id> --tag <other-tag-id>
"""

from __future__ import annotations

import argparse
import sys

from pocketai import Pocket


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--since", help="Filter from this date (YYYY-MM-DD, UTC).")
    parser.add_argument("--until", help="Filter through this date (YYYY-MM-DD, UTC).")
    parser.add_argument("--tag", action="append", default=[], help="Tag ID(s) to filter by.")
    parser.add_argument("--limit", type=int, default=20, help="Page size.")
    parser.add_argument("--max", type=int, default=100, help="Stop after this many recordings.")
    args = parser.parse_args()

    with Pocket() as client:
        page_num = 1
        seen = 0
        while True:
            page = client.recordings.list(
                start_date=args.since,
                end_date=args.until,
                tag_ids=args.tag or None,
                page=page_num,
                limit=args.limit,
            )
            for rec in page.data:
                seen += 1
                minutes = (rec.duration or 0) / 60
                print(f"{rec.id}  {rec.recording_at}  {minutes:5.1f} min  {rec.title}")
                if seen >= args.max:
                    print(f"\n(stopped at --max={args.max})")
                    return 0
            if not page.pagination.has_more:
                break
            page_num += 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
