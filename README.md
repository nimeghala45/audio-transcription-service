# Audio Transcription Service

A small Python service for uploading WAV/MP3 files, transcribing speech with faster-whisper, and retrieving transcript segments with start/end timestamps.

## Run locally

Python 3.10 or newer is recommended.

```bash
python -m venv .venv
```

Windows:
```bash
.venv\Scripts\activate
```

macOS/Linux:
```bash
source .venv/bin/activate
```

Install packages and run:

```bash
pip install -r requirements.txt
uvicorn main:app --reload
```

Open `http://127.0.0.1:8000/docs` to upload a file and inspect responses. The first transcription can download model files.

## API

- `GET /health` - basic health check.
- `POST /transcriptions` - upload a WAV or MP3 file. Returns a job ID with HTTP 202.
- `GET /transcriptions/{job_id}` - retrieve status and, once complete, timestamped segments.

Example completed response:

```json
{
  "job_id": "generated-id",
  "filename": "meeting.wav",
  "status": "completed",
  "language": "en",
  "segments": [
    {"start": 0.0, "end": 2.1, "text": "Hello there."}
  ],
  "attempts": 1,
  "error": null
}
```

## Implementation notes

- Audio is saved with a generated UUID filename so simultaneous uploads do not overwrite each other.
- File uploads are read in chunks and limited to 100 MB.
- A bounded, in-process worker pool prevents unbounded simultaneous inference.
- SQLite stores job status, language, retry count, errors, and timestamped segments.
- Temporary errors are retried up to three times with exponential backoff.
- `faster-whisper` uses PyAV to decode supported audio formats; the code does not manually convert every input file to WAV.
- This is a single-process prototype. The queue is in memory, so jobs left queued during a crash are not automatically resumed. For multi-instance production use, move jobs to a durable shared queue such as Celery with Redis and use shared object storage.
- This prototype validates file extension and size, but production code should also validate the actual audio content, add authentication/rate limits, and enforce data-retention policies.
- API tests mock job scheduling; they do not validate speech recognition accuracy. Use real sample recordings and reference transcripts to evaluate WER and latency.

## Tests

```bash
python -m unittest discover -s tests -v
```
