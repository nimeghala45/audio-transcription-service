# Audio Transcription Service

A REST API built with **Python, FastAPI, and faster-whisper** to upload audio files, process transcription jobs asynchronously, and retrieve timestamped transcript segments.

## Features

- **WAV and MP3 uploads** — accepts supported audio formats.
- **Asynchronous processing** — returns a job ID immediately so clients can check the result later.
- **Timestamped transcripts** — returns recognized speech in individual segments with start and end times.
- **Bounded job queue** — limits accepted in-progress jobs to avoid unbounded resource usage.
- **Persistent job metadata** — SQLite stores job status, language, transcript segments, attempts, errors, and timestamps.
- **Upload validation** — rejects unsupported formats, empty uploads, and files exceeding the configured size limit.
- **Error handling** — exposes job failures through the status endpoint.
- **API documentation** — interactive Swagger UI is available through FastAPI.

## Technology Stack

| Component | Technology |
|---|---|
| Language | Python |
| API framework | FastAPI |
| ASGI server | Uvicorn |
| Speech recognition | faster-whisper |
| Database | SQLite |
| Background execution | `ThreadPoolExecutor` |
| Testing | `unittest`, FastAPI `TestClient` |

## Architecture

```text
Client
  |
  | POST /transcriptions
  v
FastAPI Upload Endpoint
  |
  | Validate format and size
  | Save audio using a unique job ID
  | Create job record in SQLite
  v
Bounded In-Process Job Queue
  |
  v
Background Worker
  |
  | Transcribe audio
  | Update job status and results
  v
SQLite Job Record
  |
  | GET /transcriptions/{job_id}
  v
Client receives status and transcript
```

## Getting Started

### Requirements

- Python 3.10 or later
- `pip`
- Git

### 1. Clone the repository

```bash
git clone https://github.com/nimeghala45/audio-transcription-service.git
cd audio-transcription-service
```

### 2. Create and activate a virtual environment

**Windows PowerShell**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**macOS / Linux**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Start the API server

```bash
uvicorn main:app --reload
```

The API runs locally at:

- API base URL: `http://127.0.0.1:8000`
- Swagger UI: `http://127.0.0.1:8000/docs`
- Health check: `http://127.0.0.1:8000/health`

## API Reference

### 1. Health Check

`GET /health`

Checks whether the API is running.

Example response:

```json
{
  "status": "ok"
}
```

### 2. Submit an Audio File

`POST /transcriptions`

Uploads a WAV or MP3 file and schedules a transcription job.

Example using cURL:

```bash
curl -X POST "http://127.0.0.1:8000/transcriptions" \
  -F "file=@sample.wav"
```

Example response — `202 Accepted`:

```json
{
  "job_id": "your-job-id",
  "status": "queued",
  "status_url": "/transcriptions/your-job-id"
}
```

Save the returned `job_id` to retrieve the job's progress and result.

### 3. Retrieve a Transcription

`GET /transcriptions/{job_id}`

Returns the current status and, when available, the transcription result.

A completed job includes fields such as:

```json
{
  "job_id": "your-job-id",
  "filename": "sample.wav",
  "status": "completed",
  "language": "en",
  "segments": [
    {
      "start": 0.0,
      "end": 3.2,
      "text": "Example transcribed speech."
    }
  ],
  "attempts": 1,
  "error": null,
  "created_at": "...",
  "updated_at": "..."
}
```

The timestamps above are illustrative. Actual segment text, times, and metadata depend on the uploaded audio and job execution.

Possible job states include `queued`, `processing`, `completed`, and `failed`, depending on the worker's status transitions.

An unknown job ID returns `404 Not Found`.

## Design Decisions

### Asynchronous job submission

Transcription can take longer than an ordinary API request. The upload endpoint returns a job ID with HTTP `202 Accepted`, allowing clients to poll the status endpoint instead of waiting for the full transcription.

### Unique file naming

Each upload is stored using a unique job ID rather than the original filename. This prevents separate uploads with identical filenames from overwriting one another.

### Bounded processing

The service uses a `ThreadPoolExecutor` and a bounded semaphore to limit accepted jobs.

The current configuration uses **one worker**, so jobs are processed sequentially within a single application process. Multiple clients can submit jobs, but this implementation does not provide parallel transcription inference.

### Persistent job metadata

SQLite stores job metadata and results, including status, detected language, transcript segments, retry attempts, errors, and timestamps.

### Audio processing

The transcription worker uses faster-whisper for speech recognition. Audio decoding is handled by its underlying audio-processing dependencies, so clients do not need to convert supported files to WAV manually.

### Failure handling and retries

Job errors are recorded so clients can inspect failed jobs through the status endpoint. Transient failures can be retried with backoff if implemented by the worker.

### Upload safety

The API validates file extensions, rejects empty uploads, reads files in chunks, and enforces a configurable maximum upload size.

File extensions alone do not prove that an upload contains valid audio. Production deployments should also validate the actual media content.

## Testing

Run the API tests with:

```bash
python -m unittest discover -s tests -v
```

The API tests cover health checks, unsupported formats, empty uploads, accepted uploads, and unknown job IDs. The job scheduler is mocked in the upload test, so these tests do not independently verify speech-recognition accuracy.

For end-to-end testing, upload real WAV and MP3 samples through Swagger UI and poll their job IDs until they complete or fail.

## Current Limitations

- The job queue is in-process and is not shared across multiple application instances.
- Queued jobs may not resume automatically after an application crash.
- The current worker configuration processes one job at a time.
- SQLite is suitable for a prototype, but may not be ideal for high-volume distributed workloads.
- API authentication, rate limiting, and configurable retention policies are not included by default.

## Production Improvements

Potential next steps include:

- A durable queue such as Celery with Redis or another message broker.
- Multiple configurable workers for parallel processing.
- Recovery of queued or interrupted jobs after restarts.
- Shared object storage for uploaded audio.
- Authentication, rate limiting, and request monitoring.
- Structured logging, metrics, and integration tests using reference transcripts.
- Word Error Rate (WER), throughput, and latency measurements.

## Project Goal

This project demonstrates an asynchronous audio-transcription API with upload validation, background execution, job tracking, and timestamped transcript retrieval.

**Repository:** https://github.com/nimeghala45/audio-transcription-service
