# Examples

Runnable scripts demonstrating common workflows with `pocketai`.

Every script reads your API key from the `POCKET_API_KEY` environment variable:

```bash
export POCKET_API_KEY=pk_xxx
pip install pocketai
python examples/list_recordings.py
```

| Script | What it shows |
|---|---|
| [`list_recordings.py`](list_recordings.py) | Paginate, filter by date, filter by tag. |
| [`export_transcript.py`](export_transcript.py) | Fetch a recording with its transcript and write a timestamped Markdown file. |
| [`download_audio.py`](download_audio.py) | Fetch a signed URL and save the MP3 to disk. |
| [`upload_recording.py`](upload_recording.py) | Full upload flow: create upload URL → `PUT` bytes → poll until processed. |
| [`search_recordings.py`](search_recordings.py) | Semantic search over your recordings, transcripts, and summaries. |
| [`async_parallel_fetch.py`](async_parallel_fetch.py) | Fetch many recordings concurrently with `AsyncPocket` + `asyncio.gather`. |
| [`webhook_server.py`](webhook_server.py) | Minimal Flask app that verifies signatures and dispatches by event. |
| [`backup.py`](backup.py) | Full local backup of every recording — JSON, transcript, summary, audio. Resumable. |
