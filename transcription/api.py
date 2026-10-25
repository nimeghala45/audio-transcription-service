import logging
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile

from transcription.config import (
    AUDIO_DIR,
    MAX_QUEUED_JOBS,
    MAX_UPLOAD_BYTES,
)
from transcription.storage import create_job, create_tables, get_job
from transcription.worker import process_job

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Audio Transcription Service",
    description="Upload WAV or MP3 audio and retrieve timestamped transcript segments.",
    version="1.0.0",
)

# This is a single-process queue. Use a shared job broker for multiple instances.
worker_pool = ThreadPoolExecutor(max_workers=1)
available_slots = threading.BoundedSemaphore(MAX_QUEUED_JOBS)

SUPPORTED_FORMATS = {".wav", ".mp3"}

create_tables()


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/transcriptions", status_code=202)
async def upload_audio(file: UploadFile = File(...)):
    filename = Path(file.filename or "").name
    extension = Path(filename).suffix.lower()

    if extension not in SUPPORTED_FORMATS:
        await file.close()
        raise HTTPException(
            status_code=415,
            detail="Please upload a WAV or MP3 file.",
        )

    if not available_slots.acquire(blocking=False):
        await file.close()
        raise HTTPException(
            status_code=503,
            detail="The transcription queue is full. Please try again shortly.",
            headers={"Retry-After": "5"},
        )

    job_id = str(uuid.uuid4())
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    audio_path = AUDIO_DIR / (job_id + extension)
    total_bytes = 0
    saved = False

    try:
        with audio_path.open("wb") as output:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break

                total_bytes += len(chunk)
                if total_bytes > MAX_UPLOAD_BYTES:
                    raise HTTPException(
                        status_code=413,
                        detail="File is larger than the 100 MB limit.",
                    )
                output.write(chunk)

        if total_bytes == 0:
            raise HTTPException(status_code=400, detail="The uploaded file is empty.")

        saved = True
        create_job(job_id, filename, audio_path)

        try:
            worker_pool.submit(run_job_and_release_slot, job_id)
        except Exception:
            audio_path.unlink(missing_ok=True)
            raise HTTPException(
                status_code=503,
                detail="The transcription job could not be scheduled.",
            )

        return {
            "job_id": job_id,
            "status": "queued",
            "status_url": "/transcriptions/" + job_id,
        }
    except Exception:
        if not saved:
            audio_path.unlink(missing_ok=True)
        available_slots.release()
        raise
    finally:
        await file.close()


def run_job_and_release_slot(job_id):
    try:
        process_job(job_id)
    finally:
        available_slots.release()


@app.get("/transcriptions/{job_id}")
def read_transcription(job_id: str):
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Transcription job not found.")

    import json

    return {
        "job_id": job["job_id"],
        "filename": job["filename"],
        "status": job["status"],
        "language": job["language"],
        "segments": json.loads(job["segments"]) if job["segments"] else None,
        "attempts": job["attempts"],
        "error": job["error"],
        "created_at": job["created_at"],
        "updated_at": job["updated_at"],
    }
