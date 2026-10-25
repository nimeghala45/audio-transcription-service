import json
import sqlite3
import time

from transcription.config import DATABASE_FILE


def open_database():
    DATABASE_FILE.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE_FILE, timeout=30)
    connection.row_factory = sqlite3.Row
    return connection


def create_tables():
    with open_database() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS transcription_jobs (
                job_id TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                audio_path TEXT NOT NULL,
                status TEXT NOT NULL,
                language TEXT,
                segments TEXT,
                attempts INTEGER NOT NULL DEFAULT 0,
                error TEXT,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            )
            """
        )


def create_job(job_id, filename, audio_path):
    now = time.time()
    with open_database() as connection:
        connection.execute(
            """
            INSERT INTO transcription_jobs
            (job_id, filename, audio_path, status, created_at, updated_at)
            VALUES (?, ?, ?, 'queued', ?, ?)
            """,
            (job_id, filename, str(audio_path), now, now),
        )


def get_job(job_id):
    with open_database() as connection:
        return connection.execute(
            "SELECT * FROM transcription_jobs WHERE job_id = ?",
            (job_id,),
        ).fetchone()


def update_job(job_id, **changes):
    allowed_fields = {
        "status", "language", "segments", "attempts", "error"
    }
    if not changes or not set(changes).issubset(allowed_fields):
        raise ValueError("Invalid job update")

    changes["updated_at"] = time.time()
    assignments = ", ".join(
        "{} = ?".format(field) for field in changes
    )
    values = list(changes.values())
    values.append(job_id)

    with open_database() as connection:
        connection.execute(
            "UPDATE transcription_jobs SET {} WHERE job_id = ?".format(assignments),
            values,
        )


def save_transcript(job_id, language, segments):
    update_job(
        job_id,
        status="completed",
        language=language,
        segments=json.dumps(segments, ensure_ascii=False),
        error=None,
    )
