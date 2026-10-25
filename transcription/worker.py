import json
import logging
import time

from transcription.config import MAX_ATTEMPTS, RETRY_DELAY_SECONDS
from transcription.storage import get_job, update_job

logger = logging.getLogger(__name__)

_whisper_model = None


def load_model():
    global _whisper_model
    if _whisper_model is None:
        from faster_whisper import WhisperModel
        from transcription.config import (
            WHISPER_COMPUTE_TYPE,
            WHISPER_DEVICE,
            WHISPER_MODEL,
        )

        _whisper_model = WhisperModel(
            WHISPER_MODEL,
            device=WHISPER_DEVICE,
            compute_type=WHISPER_COMPUTE_TYPE,
        )
    return _whisper_model


def transcribe_audio(audio_path):
    model = load_model()
    segments, details = model.transcribe(audio_path, vad_filter=True)

    transcript_segments = []
    for segment in segments:
        start_time = round(float(segment.start), 3)
        end_time = round(float(segment.end), 3)

        if start_time < 0 or end_time < start_time:
            raise ValueError("The model returned invalid timestamps")

        transcript_segments.append({
            "start": start_time,
            "end": end_time,
            "text": segment.text.strip(),
        })

    return details.language, transcript_segments


def process_job(job_id):
    job = get_job(job_id)
    if job is None:
        logger.error("Could not find transcription job %s", job_id)
        return

    for attempt in range(1, MAX_ATTEMPTS + 1):
        update_job(
            job_id,
            status="processing",
            attempts=attempt,
            error=None,
        )

        try:
            language, segments = transcribe_audio(job["audio_path"])
            update_job(
                job_id,
                status="completed",
                language=language,
                segments=json.dumps(segments, ensure_ascii=False),
                error=None,
            )
            return
        except (ValueError, FileNotFoundError) as error:
            update_job(job_id, status="failed", error=str(error)[:1000])
            return
        except Exception as error:
            logger.exception(
                "Transcription attempt %s failed for job %s",
                attempt, job_id,
            )
            if attempt == MAX_ATTEMPTS:
                update_job(job_id, status="failed", error=str(error)[:1000])
                return
            time.sleep(RETRY_DELAY_SECONDS * (2 ** (attempt - 1)))
