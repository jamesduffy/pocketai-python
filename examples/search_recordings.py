"""Semantic search over your recordings, transcripts, and summaries.

Usage:
    python examples/search_recordings.py "sprint planning"
    python examples/search_recordings.py "QBR feedback" --limit 5
"""

from __future__ import annotations

import argparse
import sys
import textwrap

from pocketai import Pocket


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("query")
    parser.add_argument("--limit", type=int, default=5)
    args = parser.parse_args()

    with Pocket() as client:
        results = client.search.query(args.query, limit=args.limit)

    print(f"Query: {args.query!r}")
    print(f"Total matches: {results.total}  (timing: {results.timing} ms)\n")

    for i, memory in enumerate(results.relevant_memories, start=1):
        score = f"{memory.relevance_score:.2f}" if memory.relevance_score is not None else "n/a"
        print(f"[{i}] {memory.recording_title}  (id={memory.recording_id}, score={score})")
        for line in textwrap.wrap(memory.content, width=88):
            print(f"    {line}")
        print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
