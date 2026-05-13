"""Fetch transcripts for every recording in the last N days, in parallel.

Demonstrates ``AsyncPocket`` + ``asyncio.gather`` + a semaphore for politeness.

Usage:
    python examples/async_parallel_fetch.py --days 7 --concurrency 5
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import date, timedelta

from pocketai import AsyncPocket, Recording


async def _fetch_with_transcript(
    client: AsyncPocket,
    recording_id: str,
    sem: asyncio.Semaphore,
) -> Recording:
    async with sem:
        return await client.recordings.get(
            recording_id, include_transcript=True, include_summarizations=False
        )


async def main_async(days: int, concurrency: int) -> int:
    today = date.today()
    since = (today - timedelta(days=days)).isoformat()

    async with AsyncPocket() as client:
        page = await client.recordings.list(start_date=since, limit=100)
        ids = [r.id for r in page.data]
        if not ids:
            print(f"No recordings in the last {days} days.")
            return 0

        sem = asyncio.Semaphore(concurrency)
        print(f"Fetching {len(ids)} transcripts at concurrency={concurrency}...")
        recordings = await asyncio.gather(
            *(_fetch_with_transcript(client, rid, sem) for rid in ids),
            return_exceptions=True,
        )

    total_segments = 0
    for rec in recordings:
        if isinstance(rec, Exception):
            print(f"  ! {rec}")
            continue
        segments = rec.transcript.segments if rec.transcript else []
        total_segments += len(segments)
        print(f"  {rec.id}  {len(segments):>4d} segments  {rec.title}")

    print(f"\nFetched {total_segments} transcript segments across {len(ids)} recordings.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--concurrency", type=int, default=5)
    args = parser.parse_args()
    return asyncio.run(main_async(args.days, args.concurrency))


if __name__ == "__main__":
    sys.exit(main())
